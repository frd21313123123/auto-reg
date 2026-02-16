#include <windows.h>
#include <winhttp.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <variant>
#include <vector>

namespace {

constexpr const char* kApiBase = "https://api.mail.tm";
constexpr const char* kAccountsFile = "accounts.txt";

// ================================================================
//  Structures
// ================================================================

struct HttpResponse {
    int status_code = 0;
    std::string body;
    std::string error;
};

struct MessageSummary {
    std::string id;
    std::string sender;
    std::string subject;
    std::string created_at;
};

struct MessageDetail {
    std::string sender;
    std::string subject;
    std::string text;
    std::string html;
};

struct Account {
    std::string email;
    std::string password_openai;
    std::string password_mail;
    std::string status; // not_registered, registered, plus, banned, invalid_password
};

// ================================================================
//  Utilities
// ================================================================

std::wstring utf8ToWide(const std::string& input) {
    if (input.empty()) {
        return {};
    }
    const int needed = MultiByteToWideChar(CP_UTF8, 0, input.c_str(), -1, nullptr, 0);
    if (needed <= 0) {
        return {};
    }
    std::wstring out(static_cast<size_t>(needed - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, input.c_str(), -1, out.data(), needed);
    return out;
}

std::string trim(const std::string& s) {
    size_t begin = 0;
    while (begin < s.size() && std::isspace(static_cast<unsigned char>(s[begin])) != 0) {
        ++begin;
    }
    size_t end = s.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(s[end - 1])) != 0) {
        --end;
    }
    return s.substr(begin, end - begin);
}

std::string toLower(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return out;
}

bool endsWith(const std::string& text, const std::string& suffix) {
    if (suffix.size() > text.size()) {
        return false;
    }
    return text.compare(text.size() - suffix.size(), suffix.size(), suffix) == 0;
}

std::string extractDomain(const std::string& email) {
    size_t at_pos = email.rfind('@');
    if (at_pos == std::string::npos || at_pos + 1 >= email.size()) {
        return {};
    }
    return toLower(trim(email.substr(at_pos + 1)));
}

// ================================================================
//  RAII WinHTTP handle
// ================================================================

struct ScopedInternetHandle {
    HINTERNET handle = nullptr;
    ScopedInternetHandle() = default;
    explicit ScopedInternetHandle(HINTERNET h) : handle(h) {}
    ~ScopedInternetHandle() {
        if (handle != nullptr) {
            WinHttpCloseHandle(handle);
        }
    }
    ScopedInternetHandle(const ScopedInternetHandle&) = delete;
    ScopedInternetHandle& operator=(const ScopedInternetHandle&) = delete;
    ScopedInternetHandle(ScopedInternetHandle&& other) noexcept : handle(other.handle) {
        other.handle = nullptr;
    }
    ScopedInternetHandle& operator=(ScopedInternetHandle&& other) noexcept {
        if (this != &other) {
            if (handle != nullptr) {
                WinHttpCloseHandle(handle);
            }
            handle = other.handle;
            other.handle = nullptr;
        }
        return *this;
    }
    explicit operator bool() const {
        return handle != nullptr;
    }
};

// ================================================================
//  HTTP
// ================================================================

HttpResponse httpRequest(const std::wstring& method,
                         const std::wstring& url,
                         const std::string& body = {},
                         const std::vector<std::wstring>& headers = {},
                         int timeout_ms = 8000) {
    HttpResponse result;

    URL_COMPONENTS parts{};
    parts.dwStructSize = sizeof(parts);
    parts.dwSchemeLength = static_cast<DWORD>(-1);
    parts.dwHostNameLength = static_cast<DWORD>(-1);
    parts.dwUrlPathLength = static_cast<DWORD>(-1);
    parts.dwExtraInfoLength = static_cast<DWORD>(-1);
    if (!WinHttpCrackUrl(url.c_str(), 0, 0, &parts)) {
        result.error = "WinHttpCrackUrl failed";
        return result;
    }

    std::wstring host(parts.lpszHostName, parts.dwHostNameLength);
    std::wstring path(parts.lpszUrlPath, parts.dwUrlPathLength);
    if (parts.dwExtraInfoLength > 0) {
        path.append(parts.lpszExtraInfo, parts.dwExtraInfoLength);
    }
    if (path.empty()) {
        path = L"/";
    }
    const INTERNET_PORT port = parts.nPort;
    const bool is_https = (parts.nScheme == INTERNET_SCHEME_HTTPS);

    ScopedInternetHandle session(WinHttpOpen(
        L"auto-reg-cpp/1.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0));
    if (!session) {
        result.error = "WinHttpOpen failed";
        return result;
    }

    WinHttpSetTimeouts(session.handle, timeout_ms, timeout_ms, timeout_ms, timeout_ms);

    ScopedInternetHandle connection(
        WinHttpConnect(session.handle, host.c_str(), port, 0));
    if (!connection) {
        result.error = "WinHttpConnect failed";
        return result;
    }

    const DWORD flags = is_https ? WINHTTP_FLAG_SECURE : 0;
    ScopedInternetHandle request(WinHttpOpenRequest(
        connection.handle,
        method.c_str(),
        path.c_str(),
        nullptr,
        WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        flags));
    if (!request) {
        result.error = "WinHttpOpenRequest failed";
        return result;
    }

    for (const auto& header : headers) {
        WinHttpAddRequestHeaders(
            request.handle,
            header.c_str(),
            static_cast<DWORD>(header.size()),
            WINHTTP_ADDREQ_FLAG_ADD | WINHTTP_ADDREQ_FLAG_REPLACE);
    }

    LPVOID optional_data = body.empty() ? WINHTTP_NO_REQUEST_DATA : const_cast<char*>(body.data());
    DWORD optional_len = static_cast<DWORD>(body.size());

    if (!WinHttpSendRequest(
            request.handle,
            WINHTTP_NO_ADDITIONAL_HEADERS,
            0,
            optional_data,
            optional_len,
            optional_len,
            0)) {
        result.error = "WinHttpSendRequest failed";
        return result;
    }

    if (!WinHttpReceiveResponse(request.handle, nullptr)) {
        result.error = "WinHttpReceiveResponse failed";
        return result;
    }

    DWORD status = 0;
    DWORD status_size = sizeof(status);
    if (!WinHttpQueryHeaders(request.handle,
                             WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX,
                             &status,
                             &status_size,
                             WINHTTP_NO_HEADER_INDEX)) {
        result.error = "WinHttpQueryHeaders failed";
        return result;
    }
    result.status_code = static_cast<int>(status);

    std::string data;
    while (true) {
        DWORD available = 0;
        if (!WinHttpQueryDataAvailable(request.handle, &available)) {
            result.error = "WinHttpQueryDataAvailable failed";
            return result;
        }
        if (available == 0) {
            break;
        }
        std::string chunk(static_cast<size_t>(available), '\0');
        DWORD read = 0;
        if (!WinHttpReadData(request.handle, chunk.data(), available, &read)) {
            result.error = "WinHttpReadData failed";
            return result;
        }
        chunk.resize(static_cast<size_t>(read));
        data += chunk;
    }

    result.body = std::move(data);
    return result;
}

// ================================================================
//  JSON parser (minimal, self-contained)
// ================================================================

class Json {
public:
    using Array = std::vector<Json>;
    using Object = std::map<std::string, Json>;
    using Value = std::variant<std::nullptr_t, bool, double, std::string, Array, Object>;

    Json() : value_(nullptr) {}
    Json(std::nullptr_t) : value_(nullptr) {}
    Json(bool v) : value_(v) {}
    Json(double v) : value_(v) {}
    Json(std::string v) : value_(std::move(v)) {}
    Json(Array v) : value_(std::move(v)) {}
    Json(Object v) : value_(std::move(v)) {}

    bool isNull() const { return std::holds_alternative<std::nullptr_t>(value_); }
    bool isBool() const { return std::holds_alternative<bool>(value_); }
    bool isNumber() const { return std::holds_alternative<double>(value_); }
    bool isString() const { return std::holds_alternative<std::string>(value_); }
    bool isArray() const { return std::holds_alternative<Array>(value_); }
    bool isObject() const { return std::holds_alternative<Object>(value_); }

    const std::string& asString() const { return std::get<std::string>(value_); }
    const Array& asArray() const { return std::get<Array>(value_); }
    const Object& asObject() const { return std::get<Object>(value_); }

    const Json* get(const std::string& key) const {
        if (!isObject()) {
            return nullptr;
        }
        const auto& obj = asObject();
        auto it = obj.find(key);
        if (it == obj.end()) {
            return nullptr;
        }
        return &it->second;
    }

private:
    Value value_;
};

class JsonParser {
public:
    explicit JsonParser(const std::string& input) : src_(input), pos_(0) {}

    Json parse() {
        skipWhitespace();
        Json out = parseValue();
        skipWhitespace();
        if (pos_ != src_.size()) {
            throw std::runtime_error("Unexpected trailing JSON characters");
        }
        return out;
    }

private:
    const std::string& src_;
    size_t pos_;

    static void appendUtf8(std::string& out, uint32_t cp) {
        if (cp <= 0x7F) {
            out.push_back(static_cast<char>(cp));
        } else if (cp <= 0x7FF) {
            out.push_back(static_cast<char>(0xC0 | ((cp >> 6) & 0x1F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        } else if (cp <= 0xFFFF) {
            out.push_back(static_cast<char>(0xE0 | ((cp >> 12) & 0x0F)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        } else {
            out.push_back(static_cast<char>(0xF0 | ((cp >> 18) & 0x07)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        }
    }

    [[noreturn]] void fail(const std::string& what) const {
        std::ostringstream oss;
        oss << what << " at position " << pos_;
        throw std::runtime_error(oss.str());
    }

    void skipWhitespace() {
        while (pos_ < src_.size() &&
               (src_[pos_] == ' ' || src_[pos_] == '\n' || src_[pos_] == '\r' || src_[pos_] == '\t')) {
            ++pos_;
        }
    }

    char peek() const {
        if (pos_ >= src_.size()) {
            return '\0';
        }
        return src_[pos_];
    }

    char take() {
        if (pos_ >= src_.size()) {
            fail("Unexpected end of JSON");
        }
        return src_[pos_++];
    }

    bool consume(char c) {
        if (peek() == c) {
            ++pos_;
            return true;
        }
        return false;
    }

    Json parseValue() {
        switch (peek()) {
            case '{':
                return parseObject();
            case '[':
                return parseArray();
            case '"':
                return Json(parseString());
            case 't':
                parseLiteral("true");
                return Json(true);
            case 'f':
                parseLiteral("false");
                return Json(false);
            case 'n':
                parseLiteral("null");
                return Json(nullptr);
            default:
                if (peek() == '-' || std::isdigit(static_cast<unsigned char>(peek())) != 0) {
                    return Json(parseNumber());
                }
                fail("Unexpected JSON token");
        }
    }

    void parseLiteral(const char* literal) {
        while (*literal != '\0') {
            if (take() != *literal) {
                fail("Invalid JSON literal");
            }
            ++literal;
        }
    }

    uint32_t parseHex4() {
        uint32_t v = 0;
        for (int i = 0; i < 4; ++i) {
            const char c = take();
            v <<= 4;
            if (c >= '0' && c <= '9') {
                v |= static_cast<uint32_t>(c - '0');
            } else if (c >= 'a' && c <= 'f') {
                v |= static_cast<uint32_t>(10 + c - 'a');
            } else if (c >= 'A' && c <= 'F') {
                v |= static_cast<uint32_t>(10 + c - 'A');
            } else {
                fail("Invalid \\u escape");
            }
        }
        return v;
    }

    std::string parseString() {
        if (!consume('"')) {
            fail("Expected string");
        }
        std::string out;
        while (true) {
            const char c = take();
            if (c == '"') {
                return out;
            }
            if (c == '\\') {
                const char esc = take();
                switch (esc) {
                    case '"':
                    case '\\':
                    case '/':
                        out.push_back(esc);
                        break;
                    case 'b':
                        out.push_back('\b');
                        break;
                    case 'f':
                        out.push_back('\f');
                        break;
                    case 'n':
                        out.push_back('\n');
                        break;
                    case 'r':
                        out.push_back('\r');
                        break;
                    case 't':
                        out.push_back('\t');
                        break;
                    case 'u': {
                        uint32_t code = parseHex4();
                        if (code >= 0xD800 && code <= 0xDBFF) {
                            const size_t saved = pos_;
                            if (consume('\\') && consume('u')) {
                                uint32_t low = parseHex4();
                                if (low >= 0xDC00 && low <= 0xDFFF) {
                                    code = 0x10000 + (((code - 0xD800) << 10) | (low - 0xDC00));
                                } else {
                                    pos_ = saved;
                                }
                            } else {
                                pos_ = saved;
                            }
                        }
                        appendUtf8(out, code);
                        break;
                    }
                    default:
                        fail("Invalid string escape");
                }
            } else {
                if (static_cast<unsigned char>(c) < 0x20) {
                    fail("Invalid control character in string");
                }
                out.push_back(c);
            }
        }
    }

    double parseNumber() {
        size_t start = pos_;
        if (peek() == '-') {
            ++pos_;
        }
        if (peek() == '0') {
            ++pos_;
        } else if (std::isdigit(static_cast<unsigned char>(peek())) != 0) {
            while (std::isdigit(static_cast<unsigned char>(peek())) != 0) {
                ++pos_;
            }
        } else {
            fail("Invalid number");
        }

        if (peek() == '.') {
            ++pos_;
            if (std::isdigit(static_cast<unsigned char>(peek())) == 0) {
                fail("Invalid number fraction");
            }
            while (std::isdigit(static_cast<unsigned char>(peek())) != 0) {
                ++pos_;
            }
        }

        if (peek() == 'e' || peek() == 'E') {
            ++pos_;
            if (peek() == '+' || peek() == '-') {
                ++pos_;
            }
            if (std::isdigit(static_cast<unsigned char>(peek())) == 0) {
                fail("Invalid exponent");
            }
            while (std::isdigit(static_cast<unsigned char>(peek())) != 0) {
                ++pos_;
            }
        }

        const std::string token = src_.substr(start, pos_ - start);
        try {
            return std::stod(token);
        } catch (...) {
            fail("Cannot parse number");
        }
    }

    Json parseArray() {
        if (!consume('[')) {
            fail("Expected array");
        }
        Json::Array items;
        skipWhitespace();
        if (consume(']')) {
            return Json(std::move(items));
        }
        while (true) {
            skipWhitespace();
            items.push_back(parseValue());
            skipWhitespace();
            if (consume(']')) {
                break;
            }
            if (!consume(',')) {
                fail("Expected ',' in array");
            }
        }
        return Json(std::move(items));
    }

    Json parseObject() {
        if (!consume('{')) {
            fail("Expected object");
        }
        Json::Object out;
        skipWhitespace();
        if (consume('}')) {
            return Json(std::move(out));
        }
        while (true) {
            skipWhitespace();
            if (peek() != '"') {
                fail("Expected key string");
            }
            const std::string key = parseString();
            skipWhitespace();
            if (!consume(':')) {
                fail("Expected ':' after key");
            }
            skipWhitespace();
            out.emplace(key, parseValue());
            skipWhitespace();
            if (consume('}')) {
                break;
            }
            if (!consume(',')) {
                fail("Expected ',' in object");
            }
        }
        return Json(std::move(out));
    }
};

std::optional<Json> parseJsonSafe(const std::string& text, std::string* error_out = nullptr) {
    try {
        JsonParser parser(text);
        return parser.parse();
    } catch (const std::exception& ex) {
        if (error_out != nullptr) {
            *error_out = ex.what();
        }
        return std::nullopt;
    }
}

std::string jsonEscape(const std::string& s) {
    std::ostringstream out;
    for (unsigned char c : s) {
        switch (c) {
            case '"':
                out << "\\\"";
                break;
            case '\\':
                out << "\\\\";
                break;
            case '\b':
                out << "\\b";
                break;
            case '\f':
                out << "\\f";
                break;
            case '\n':
                out << "\\n";
                break;
            case '\r':
                out << "\\r";
                break;
            case '\t':
                out << "\\t";
                break;
            default:
                if (c < 0x20) {
                    out << "\\u"
                        << std::hex << std::uppercase << std::setw(4) << std::setfill('0')
                        << static_cast<int>(c)
                        << std::dec << std::nouppercase;
                } else {
                    out << static_cast<char>(c);
                }
        }
    }
    return out.str();
}

std::string randomString(size_t len, const std::string& alphabet) {
    static thread_local std::mt19937_64 rng(
        static_cast<unsigned long long>(
            std::chrono::high_resolution_clock::now().time_since_epoch().count()) ^
        static_cast<unsigned long long>(std::hash<std::thread::id>{}(std::this_thread::get_id())));
    std::uniform_int_distribution<size_t> dist(0, alphabet.size() - 1);
    std::string out;
    out.reserve(len);
    for (size_t i = 0; i < len; ++i) {
        out.push_back(alphabet[dist(rng)]);
    }
    return out;
}

// ================================================================
//  Account file operations
// ================================================================

bool parsePasswords(const std::string& source, Account* acc) {
    std::string passwords = trim(source);
    if (passwords.empty()) {
        return false;
    }

    size_t semi = passwords.find(';');
    if (semi != std::string::npos) {
        acc->password_openai = trim(passwords.substr(0, semi));
        acc->password_mail = trim(passwords.substr(semi + 1));
    } else {
        acc->password_openai = passwords;
        acc->password_mail = passwords;
    }

    if (acc->password_openai.empty() && !acc->password_mail.empty()) {
        acc->password_openai = acc->password_mail;
    } else if (acc->password_mail.empty() && !acc->password_openai.empty()) {
        acc->password_mail = acc->password_openai;
    }

    return !acc->password_openai.empty() || !acc->password_mail.empty();
}

bool parseAccountLine(const std::string& line_in, Account* out, bool* used_legacy_format) {
    std::string line = trim(line_in);
    if (line.empty()) {
        return false;
    }

    Account acc;
    acc.status = "not_registered";

    // Format: email / password_openai;password_mail / status
    if (line.find(" / ") != std::string::npos) {
        size_t first = line.find(" / ");
        acc.email = trim(line.substr(0, first));
        std::string rest = line.substr(first + 3);

        size_t second = rest.find(" / ");
        std::string passwords;
        if (second != std::string::npos) {
            passwords = trim(rest.substr(0, second));
            std::string parsed_status = trim(rest.substr(second + 3));
            if (!parsed_status.empty()) {
                acc.status = parsed_status;
            }
        } else {
            passwords = trim(rest);
        }

        if (!parsePasswords(passwords, &acc)) {
            return false;
        }
    }
    // Legacy format: email:password_openai;password_mail
    else if (line.find(':') != std::string::npos) {
        size_t colon = line.find(':');
        acc.email = trim(line.substr(0, colon));
        std::string passwords = trim(line.substr(colon + 1));
        if (!parsePasswords(passwords, &acc)) {
            return false;
        }
        if (used_legacy_format != nullptr) {
            *used_legacy_format = true;
        }
    }
    // Legacy tab-separated import: email\tpassword_openai;password_mail
    else if (line.find('\t') != std::string::npos) {
        size_t tab = line.find('\t');
        acc.email = trim(line.substr(0, tab));
        std::string passwords = trim(line.substr(tab + 1));
        if (!parsePasswords(passwords, &acc)) {
            return false;
        }
        if (used_legacy_format != nullptr) {
            *used_legacy_format = true;
        }
    } else {
        return false;
    }

    if (acc.email.empty()) {
        return false;
    }

    *out = std::move(acc);
    return true;
}

std::string serializePasswords(const Account& acc) {
    std::string password_openai = trim(acc.password_openai);
    std::string password_mail = trim(acc.password_mail);

    if (!password_openai.empty() && !password_mail.empty() && password_openai != password_mail) {
        return password_openai + ";" + password_mail;
    }
    if (!password_mail.empty()) {
        return password_mail;
    }
    return password_openai;
}

std::vector<Account> loadAccounts(bool* needs_rewrite = nullptr) {
    if (needs_rewrite != nullptr) {
        *needs_rewrite = false;
    }

    std::vector<Account> accounts;
    std::ifstream in(kAccountsFile);
    if (!in.is_open()) {
        return accounts;
    }

    std::string line;
    while (std::getline(in, line)) {
        Account acc;
        bool used_legacy_format = false;
        if (parseAccountLine(line, &acc, &used_legacy_format)) {
            accounts.push_back(std::move(acc));
            if (used_legacy_format && needs_rewrite != nullptr) {
                *needs_rewrite = true;
            }
        }
    }
    return accounts;
}

void saveAccounts(const std::vector<Account>& accounts) {
    std::ofstream out(kAccountsFile, std::ios::trunc);
    if (!out.is_open()) {
        std::cerr << "Warning: cannot open " << kAccountsFile << " for writing.\n";
        return;
    }
    for (const auto& acc : accounts) {
        std::string passwords = serializePasswords(acc);
        out << acc.email << " / " << passwords << " / " << acc.status << "\n";
    }
}

void appendAccount(const std::string& email, const std::string& password) {
    std::ofstream out(kAccountsFile, std::ios::app);
    if (!out.is_open()) {
        std::cerr << "Warning: cannot open " << kAccountsFile << " for writing.\n";
        return;
    }
    out << email << " / " << password << " / not_registered\n";
}

// ================================================================
//  API functions
// ================================================================

std::optional<std::string> extractDetail(const std::string& body) {
    auto root = parseJsonSafe(body);
    if (!root.has_value() || !root->isObject()) {
        return std::nullopt;
    }
    const Json* detail = root->get("detail");
    if (detail != nullptr && detail->isString()) {
        return detail->asString();
    }
    return std::nullopt;
}

std::optional<std::vector<std::string>> getDomains(std::string* error) {
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/domains");
    HttpResponse res = httpRequest(L"GET", url);
    if (!res.error.empty()) {
        if (error != nullptr) {
            *error = res.error;
        }
        return std::nullopt;
    }
    if (res.status_code != 200) {
        if (error != nullptr) {
            std::ostringstream oss;
            oss << "HTTP " << res.status_code;
            *error = oss.str();
        }
        return std::nullopt;
    }

    auto root = parseJsonSafe(res.body, error);
    if (!root.has_value() || !root->isObject()) {
        if (error != nullptr && error->empty()) {
            *error = "Invalid domains JSON";
        }
        return std::nullopt;
    }
    const Json* members = root->get("hydra:member");
    if (members == nullptr || !members->isArray()) {
        if (error != nullptr) {
            *error = "Response missing hydra:member";
        }
        return std::nullopt;
    }
    std::vector<std::string> domains;
    for (const auto& entry : members->asArray()) {
        const Json* domain = entry.get("domain");
        if (domain != nullptr && domain->isString()) {
            domains.push_back(domain->asString());
        }
    }
    if (domains.empty()) {
        if (error != nullptr) {
            *error = "No domains returned by API";
        }
        return std::nullopt;
    }
    return domains;
}

const std::vector<std::string>& getMailTmDomainsCached() {
    static std::once_flag once;
    static std::vector<std::string> cache;

    std::call_once(once, []() {
        std::string error;
        auto domains_opt = getDomains(&error);
        if (!domains_opt.has_value()) {
            return;
        }
        cache.reserve(domains_opt->size());
        for (const auto& domain : *domains_opt) {
            cache.push_back(toLower(trim(domain)));
        }
    });

    return cache;
}

bool isMailTmAccount(const std::string& email) {
    std::string domain = extractDomain(email);
    if (domain.empty()) {
        return false;
    }

    if (domain == "mail.tm" || endsWith(domain, ".mail.tm")) {
        return true;
    }

    const auto& domains = getMailTmDomainsCached();
    return std::find(domains.begin(), domains.end(), domain) != domains.end();
}

bool createAccount(const std::string& email,
                   const std::string& password,
                   std::string* error) {
    std::ostringstream body;
    body << "{\"address\":\"" << jsonEscape(email) << "\",\"password\":\"" << jsonEscape(password) << "\"}";

    std::vector<std::wstring> headers{
        L"Content-Type: application/json",
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/accounts");
    HttpResponse res = httpRequest(L"POST", url, body.str(), headers);

    if (!res.error.empty()) {
        if (error != nullptr) {
            *error = res.error;
        }
        return false;
    }
    if (res.status_code == 201) {
        return true;
    }

    if (error != nullptr) {
        std::ostringstream oss;
        oss << "HTTP " << res.status_code;
        auto detail = extractDetail(res.body);
        if (detail.has_value()) {
            oss << ": " << *detail;
        }
        *error = oss.str();
    }
    return false;
}

std::optional<std::string> getToken(const std::string& email,
                                    const std::string& password,
                                    std::string* error,
                                    int timeout_ms = 8000) {
    std::ostringstream body;
    body << "{\"address\":\"" << jsonEscape(email) << "\",\"password\":\"" << jsonEscape(password) << "\"}";

    std::vector<std::wstring> headers{
        L"Content-Type: application/json",
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/token");
    HttpResponse res = httpRequest(L"POST", url, body.str(), headers, timeout_ms);

    if (!res.error.empty()) {
        if (error != nullptr) {
            *error = res.error;
        }
        return std::nullopt;
    }
    if (res.status_code == 401) {
        if (error != nullptr) {
            *error = "invalid_password";
        }
        return std::nullopt;
    }
    if (res.status_code != 200) {
        if (error != nullptr) {
            std::ostringstream oss;
            oss << "HTTP " << res.status_code;
            auto detail = extractDetail(res.body);
            if (detail.has_value()) {
                oss << ": " << *detail;
            }
            *error = oss.str();
        }
        return std::nullopt;
    }

    auto root = parseJsonSafe(res.body, error);
    if (!root.has_value() || !root->isObject()) {
        if (error != nullptr && error->empty()) {
            *error = "Invalid token JSON";
        }
        return std::nullopt;
    }
    const Json* token = root->get("token");
    if (token == nullptr || !token->isString()) {
        if (error != nullptr) {
            *error = "Token field missing";
        }
        return std::nullopt;
    }
    return token->asString();
}

std::optional<std::vector<MessageSummary>> getMessages(const std::string& token,
                                                       std::string* error,
                                                       int timeout_ms = 8000) {
    std::vector<std::wstring> headers{
        utf8ToWide(std::string("Authorization: Bearer ") + token),
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/messages?page=1");
    HttpResponse res = httpRequest(L"GET", url, {}, headers, timeout_ms);

    if (!res.error.empty()) {
        if (error != nullptr) {
            *error = res.error;
        }
        return std::nullopt;
    }
    if (res.status_code != 200) {
        if (error != nullptr) {
            std::ostringstream oss;
            oss << "HTTP " << res.status_code;
            *error = oss.str();
        }
        return std::nullopt;
    }

    auto root = parseJsonSafe(res.body, error);
    if (!root.has_value() || !root->isObject()) {
        if (error != nullptr && error->empty()) {
            *error = "Invalid messages JSON";
        }
        return std::nullopt;
    }
    const Json* members = root->get("hydra:member");
    if (members == nullptr || !members->isArray()) {
        if (error != nullptr) {
            *error = "Response missing hydra:member";
        }
        return std::nullopt;
    }

    std::vector<MessageSummary> messages;
    for (const auto& item : members->asArray()) {
        if (!item.isObject()) {
            continue;
        }
        MessageSummary m;
        const Json* id = item.get("id");
        if (id != nullptr && id->isString()) {
            m.id = id->asString();
        }
        const Json* subject = item.get("subject");
        if (subject != nullptr && subject->isString()) {
            m.subject = subject->asString();
        } else {
            m.subject = "(no subject)";
        }
        const Json* created = item.get("createdAt");
        if (created != nullptr && created->isString()) {
            m.created_at = created->asString();
        }
        const Json* from = item.get("from");
        if (from != nullptr && from->isObject()) {
            const Json* addr = from->get("address");
            if (addr != nullptr && addr->isString()) {
                m.sender = addr->asString();
            }
        }
        if (m.sender.empty()) {
            m.sender = "Unknown sender";
        }
        if (!m.id.empty()) {
            messages.push_back(std::move(m));
        }
    }
    return messages;
}

std::optional<MessageDetail> getMessageDetail(const std::string& token,
                                              const std::string& message_id,
                                              std::string* error) {
    std::vector<std::wstring> headers{
        utf8ToWide(std::string("Authorization: Bearer ") + token),
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/messages/" + message_id);
    HttpResponse res = httpRequest(L"GET", url, {}, headers);

    if (!res.error.empty()) {
        if (error != nullptr) {
            *error = res.error;
        }
        return std::nullopt;
    }
    if (res.status_code != 200) {
        if (error != nullptr) {
            std::ostringstream oss;
            oss << "HTTP " << res.status_code;
            *error = oss.str();
        }
        return std::nullopt;
    }

    auto root = parseJsonSafe(res.body, error);
    if (!root.has_value() || !root->isObject()) {
        if (error != nullptr && error->empty()) {
            *error = "Invalid message JSON";
        }
        return std::nullopt;
    }

    MessageDetail detail;
    const Json* from = root->get("from");
    if (from != nullptr && from->isObject()) {
        const Json* addr = from->get("address");
        if (addr != nullptr && addr->isString()) {
            detail.sender = addr->asString();
        }
    }
    const Json* subject = root->get("subject");
    if (subject != nullptr && subject->isString()) {
        detail.subject = subject->asString();
    }
    const Json* text = root->get("text");
    if (text != nullptr && text->isString()) {
        detail.text = text->asString();
    }
    const Json* html = root->get("html");
    if (html != nullptr && html->isString()) {
        detail.html = html->asString();
    }
    return detail;
}

// ================================================================
//  Ban check (multi-threaded)
// ================================================================

enum class BanResult { ok, banned, invalid_password, unsupported_domain, error };

struct BanCheckResult {
    size_t index;
    BanResult result;
    std::string reason;
};

BanCheckResult checkAccountForBan(size_t idx, const Account& acc) {
    BanCheckResult out{idx, BanResult::ok, ""};

    if (acc.email.empty() || acc.password_mail.empty()) {
        return out;
    }
    if (acc.status == "banned" || acc.status == "invalid_password") {
        return out; // skip already marked
    }

    // Always try mail.tm API — domains may not end with "mail.tm"
    std::string error;
    auto token_opt = getToken(acc.email, acc.password_mail, &error, 5000);
    if (!token_opt.has_value()) {
        if (error == "invalid_password") {
            out.result = BanResult::invalid_password;
            out.reason = "wrong_credentials";
        } else {
            out.result = BanResult::error;
            out.reason = error;
        }
        return out;
    }

    auto messages_opt = getMessages(*token_opt, &error, 5000);
    if (!messages_opt.has_value()) {
        out.result = BanResult::error;
        out.reason = error;
        return out;
    }

    // Ключевые слова бана — соответствует Python-реализации
    static const std::vector<std::string> ban_keywords = {
        "access deactivated", "deactivated", "account suspended",
        "account disabled", "account has been disabled",
        "account has been deactivated", "suspended", "violation",
    };

    for (const auto& msg : *messages_opt) {
        std::string sender_lower = toLower(msg.sender);
        std::string subject_lower = toLower(msg.subject);

        if (sender_lower.find("openai") == std::string::npos)
            continue;

        for (const auto& kw : ban_keywords) {
            if (subject_lower.find(kw) != std::string::npos) {
                out.result = BanResult::banned;
                out.reason = "access_deactivated";
                return out;
            }
        }
    }

    return out;
}

void handleBanCheck() {
    bool needs_rewrite = false;
    auto accounts = loadAccounts(&needs_rewrite);
    if (accounts.empty()) {
        std::cout << "No accounts in " << kAccountsFile << "\n";
        return;
    }
    if (needs_rewrite) {
        saveAccounts(accounts);
        std::cout << "Legacy account format converted to canonical format.\n";
    }

    const size_t total = accounts.size();
    size_t to_check = 0;
    for (const auto& acc : accounts) {
        if (acc.status != "banned" && acc.status != "invalid_password" &&
            !acc.email.empty() && !acc.password_mail.empty()) {
            ++to_check;
        }
    }

    std::cout << "Accounts: " << total << " total, " << to_check << " to check.\n";
    if (to_check == 0) {
        std::cout << "Nothing to check.\n";
        return;
    }

    // Thread count: up to 60, I/O-bound
    const size_t max_threads = std::min<size_t>(60, std::max<size_t>(8, to_check / 3));
    const size_t thread_count = std::min(to_check, max_threads);
    std::cout << "Using " << thread_count << " threads...\n";

    std::atomic<size_t> checked{0};
    std::atomic<size_t> banned{0};
    std::atomic<size_t> invalid_pass{0};
    std::atomic<size_t> unsupported{0};
    std::mutex results_mutex;
    std::vector<BanCheckResult> results;

    // Work queue
    std::atomic<size_t> next_idx{0};
    auto start_time = std::chrono::steady_clock::now();

    auto worker = [&]() {
        while (true) {
            size_t idx = next_idx.fetch_add(1);
            if (idx >= total) {
                break;
            }

            auto res = checkAccountForBan(idx, accounts[idx]);
            size_t done = checked.fetch_add(1) + 1;

            if (res.result == BanResult::banned) {
                banned.fetch_add(1);
                std::lock_guard<std::mutex> lock(results_mutex);
                results.push_back(res);
            } else if (res.result == BanResult::invalid_password) {
                invalid_pass.fetch_add(1);
                std::lock_guard<std::mutex> lock(results_mutex);
                results.push_back(res);
            } else if (res.result == BanResult::unsupported_domain) {
                unsupported.fetch_add(1);
            }

            // Print progress every ~10 accounts
            if (done % 10 == 0 || done == total) {
                auto now = std::chrono::steady_clock::now();
                double elapsed = std::chrono::duration<double>(now - start_time).count();
                double speed = static_cast<double>(done) / std::max(elapsed, 0.1);
                double remaining = static_cast<double>(total - done) / std::max(speed, 0.1);
                std::cout << "\r  [" << done << "/" << total << "] "
                          << std::fixed << std::setprecision(1)
                          << speed << " acc/s | ~" << remaining << "s left"
                          << "    " << std::flush;
            }
        }
    };

    // Launch threads
    std::vector<std::thread> threads;
    threads.reserve(thread_count);
    for (size_t i = 0; i < thread_count; ++i) {
        threads.emplace_back(worker);
    }
    for (auto& t : threads) {
        t.join();
    }

    auto end_time = std::chrono::steady_clock::now();
    double total_time = std::chrono::duration<double>(end_time - start_time).count();

    // Apply results
    for (const auto& r : results) {
        if (r.result == BanResult::banned) {
            accounts[r.index].status = "banned";
        } else if (r.result == BanResult::invalid_password) {
            accounts[r.index].status = "invalid_password";
        }
    }
    saveAccounts(accounts);

    std::cout << "\n\nDone in " << std::fixed << std::setprecision(1) << total_time << "s"
              << " (" << std::setprecision(1) << (static_cast<double>(total) / std::max(total_time, 0.1))
              << " acc/s)\n";
    std::cout << "  Checked: " << checked.load() << "\n";
    std::cout << "  Banned: " << banned.load() << "\n";
    std::cout << "  Invalid password: " << invalid_pass.load() << "\n";
    std::cout << "  Unsupported (non-mail.tm): " << unsupported.load() << "\n";
    std::cout << "  File saved: " << kAccountsFile << "\n";
}

// ================================================================
//  Batch account creation
// ================================================================

std::string promptLine(const std::string& label, bool allow_empty = false);
int promptInt(const std::string& label, int min_value, int max_value, int default_value);

void handleBatchCreate() {
    std::string error;
    auto domains_opt = getDomains(&error);
    if (!domains_opt.has_value()) {
        std::cerr << "Cannot fetch domains: " << error << "\n";
        return;
    }
    const auto& domains = *domains_opt;

    int count = promptInt("How many accounts to create [1-100]: ", 1, 100, 1);

    std::cout << "Creating " << count << " accounts...\n";

    int created = 0;
    int failed = 0;

    for (int i = 0; i < count; ++i) {
        // Pick random domain
        std::uniform_int_distribution<size_t> dist(0, domains.size() - 1);
        static std::mt19937_64 rng(
            static_cast<unsigned long long>(
                std::chrono::high_resolution_clock::now().time_since_epoch().count()));
        const std::string& domain = domains[dist(rng)];

        std::string local = randomString(10, "abcdefghijklmnopqrstuvwxyz0123456789");
        std::string password = randomString(12, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789");
        std::string email = local + "@" + domain;

        std::string err;
        if (createAccount(email, password, &err)) {
            appendAccount(email, password);
            ++created;
            std::cout << "  [" << (i + 1) << "/" << count << "] " << email << " OK\n";
        } else {
            ++failed;
            std::cout << "  [" << (i + 1) << "/" << count << "] " << email << " FAIL: " << err << "\n";
        }
    }

    std::cout << "\nCreated: " << created << ", Failed: " << failed << "\n";
}

// ================================================================
//  UI helpers
// ================================================================

std::string promptLine(const std::string& label, bool allow_empty) {
    while (true) {
        std::cout << label;
        std::string line;
        std::getline(std::cin, line);
        line = trim(line);
        if (allow_empty || !line.empty()) {
            return line;
        }
    }
}

int promptInt(const std::string& label, int min_value, int max_value, int default_value) {
    while (true) {
        std::cout << label;
        std::string line;
        std::getline(std::cin, line);
        line = trim(line);
        if (line.empty()) {
            return default_value;
        }
        try {
            int v = std::stoi(line);
            if (v >= min_value && v <= max_value) {
                return v;
            }
        } catch (...) {
        }
        std::cout << "Enter a number from " << min_value << " to " << max_value << ".\n";
    }
}

void printMessages(const std::vector<MessageSummary>& messages) {
    if (messages.empty()) {
        std::cout << "Inbox is empty.\n";
        return;
    }
    std::cout << "\nInbox messages (" << messages.size() << "):\n";
    for (size_t i = 0; i < messages.size(); ++i) {
        const auto& m = messages[i];
        std::cout << std::setw(2) << (i + 1) << ". "
                  << m.sender << " | "
                  << m.subject << " | "
                  << m.created_at << "\n";
    }
}

void printMessageCodes(const std::string& text) {
    std::regex code_regex(R"(\b\d{6}\b)");
    auto begin = std::sregex_iterator(text.begin(), text.end(), code_regex);
    auto end = std::sregex_iterator();
    std::vector<std::string> codes;
    for (auto it = begin; it != end; ++it) {
        codes.push_back(it->str());
    }
    if (!codes.empty()) {
        std::cout << "Detected 6-digit codes: ";
        for (size_t i = 0; i < codes.size(); ++i) {
            if (i > 0) {
                std::cout << ", ";
            }
            std::cout << codes[i];
        }
        std::cout << "\n";
    }
}

// ================================================================
//  Menu handlers
// ================================================================

void handleCreateAccount() {
    std::string error;
    auto domains_opt = getDomains(&error);
    if (!domains_opt.has_value()) {
        std::cerr << "Cannot fetch domains: " << error << "\n";
        return;
    }
    const auto& domains = *domains_opt;

    std::cout << "\nAvailable domains:\n";
    const size_t shown = std::min<size_t>(domains.size(), 10);
    for (size_t i = 0; i < shown; ++i) {
        std::cout << "  " << (i + 1) << ". " << domains[i] << "\n";
    }

    int domain_idx = promptInt("Choose domain index [default 1]: ", 1, static_cast<int>(shown), 1);
    const std::string domain = domains[static_cast<size_t>(domain_idx - 1)];

    std::string local = promptLine("Local part (empty = auto): ", true);
    if (local.empty()) {
        local = randomString(12, "abcdefghijklmnopqrstuvwxyz0123456789");
    }

    std::string password = promptLine("Password (empty = auto): ", true);
    if (password.empty()) {
        password = randomString(14, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789");
    }

    const std::string email = local + "@" + domain;
    std::cout << "Creating account " << email << " ...\n";

    if (!createAccount(email, password, &error)) {
        std::cerr << "Create failed: " << error << "\n";
        return;
    }

    appendAccount(email, password);
    std::cout << "Account created and appended to " << kAccountsFile << ".\n";
    std::cout << "Email: " << email << "\n";
    std::cout << "Password: " << password << "\n";
}

void handleInbox() {
    std::string email = promptLine("Email: ");
    std::string password = promptLine("Password: ");

    // Always try mail.tm API — domains may not end with "mail.tm"
    std::string error;
    auto token_opt = getToken(email, password, &error);
    if (!token_opt.has_value()) {
        std::cerr << "Login failed: " << error << "\n";
        return;
    }

    auto messages_opt = getMessages(*token_opt, &error);
    if (!messages_opt.has_value()) {
        std::cerr << "Cannot load inbox: " << error << "\n";
        return;
    }

    auto messages = *messages_opt;
    printMessages(messages);
    if (messages.empty()) {
        return;
    }

    while (true) {
        int idx = promptInt("\nOpen message # (0 = back): ",
                            0,
                            static_cast<int>(messages.size()),
                            0);
        if (idx == 0) {
            return;
        }
        const auto& selected = messages[static_cast<size_t>(idx - 1)];
        auto detail_opt = getMessageDetail(*token_opt, selected.id, &error);
        if (!detail_opt.has_value()) {
            std::cerr << "Cannot load message: " << error << "\n";
            continue;
        }
        const auto& d = *detail_opt;
        std::cout << "\nFrom: " << (d.sender.empty() ? selected.sender : d.sender) << "\n";
        std::cout << "Subject: " << (d.subject.empty() ? selected.subject : d.subject) << "\n";
        std::cout << "----------------------------------------\n";
        if (!d.text.empty()) {
            std::cout << d.text << "\n";
            printMessageCodes(d.text);
        } else if (!d.html.empty()) {
            std::cout << d.html << "\n";
            printMessageCodes(d.html);
        } else {
            std::cout << "(empty message body)\n";
        }
    }
}

void handleListAccounts() {
    bool needs_rewrite = false;
    auto accounts = loadAccounts(&needs_rewrite);
    if (accounts.empty()) {
        std::cout << "No accounts in " << kAccountsFile << "\n";
        return;
    }
    if (needs_rewrite) {
        saveAccounts(accounts);
        std::cout << "Legacy account format converted to canonical format.\n";
    }

    std::cout << "\nAccounts (" << accounts.size() << "):\n";
    for (size_t i = 0; i < accounts.size(); ++i) {
        std::string status_tag;
        if (accounts[i].status == "registered") {
            status_tag = " [REG]";
        } else if (accounts[i].status == "plus") {
            status_tag = " [PLUS]";
        } else if (accounts[i].status == "banned") {
            status_tag = " [BANNED]";
        } else if (accounts[i].status == "invalid_password") {
            status_tag = " [BAD PASS]";
        }
        std::cout << std::setw(3) << (i + 1) << ". " << accounts[i].email << status_tag << "\n";
    }
}

void printMenu() {
    std::cout << "\n=== auto-reg C++ (mail.tm) ===\n"
              << "1. Create account (interactive)\n"
              << "2. Batch create accounts\n"
              << "3. Login + read inbox (mail.tm API)\n"
              << "4. List accounts\n"
              << "5. Ban check (multi-threaded, non-mail.tm skipped)\n"
              << "6. Exit\n";
}

}  // namespace

namespace {

namespace fs = std::filesystem;

constexpr int IDC_BTN_CREATE = 1101;
constexpr int IDC_BTN_RELOAD = 1102;
constexpr int IDC_BTN_COPY_EMAIL = 1103;
constexpr int IDC_LIST_ACCOUNTS = 1104;
constexpr int IDC_LABEL_EMAIL = 1105;
constexpr int IDC_BTN_REFRESH = 1106;
constexpr int IDC_LIST_MESSAGES = 1107;
constexpr int IDC_EDIT_MESSAGE = 1108;
constexpr int IDC_STATUS = 1109;
constexpr int IDC_TITLE = 1110;
constexpr int IDC_BTN_COPY_FULL = 1111;
constexpr int IDC_BTN_BACKUP = 1112;
constexpr int IDC_BTN_ANALYTICS = 1113;

constexpr UINT WM_APP_INBOX_READY = WM_APP + 101;
constexpr UINT WM_APP_MESSAGE_READY = WM_APP + 102;
constexpr UINT WM_APP_CREATE_READY = WM_APP + 103;

constexpr COLORREF COLOR_BG = RGB(11, 16, 32);
constexpr COLORREF COLOR_PANEL = RGB(17, 24, 43);
constexpr COLORREF COLOR_HEADER = RGB(21, 33, 58);
constexpr COLORREF COLOR_STATUS = RGB(14, 22, 42);
constexpr COLORREF COLOR_CONTROL = RGB(19, 28, 50);
constexpr COLORREF COLOR_TEXT = RGB(234, 241, 255);
constexpr COLORREF COLOR_MUTED = RGB(143, 164, 204);
constexpr COLORREF COLOR_ACCENT = RGB(58, 123, 255);

struct GuiInboxResult {
    bool success = false;
    std::string email;
    std::string password;
    std::string token;
    std::vector<MessageSummary> messages;
    std::string error;
};

struct GuiMessageResult {
    bool success = false;
    std::string sender;
    std::string subject;
    std::string content;
    std::string error;
};

struct GuiCreateResult {
    bool success = false;
    Account account;
    std::string error;
};

struct GuiState {
    HWND hwnd = nullptr;

    HWND title = nullptr;
    HWND btn_create = nullptr;
    HWND btn_reload = nullptr;
    HWND btn_copy_email = nullptr;
    HWND btn_copy_full = nullptr;
    HWND btn_backup = nullptr;
    HWND btn_analytics = nullptr;
    HWND list_accounts = nullptr;

    HWND label_email = nullptr;
    HWND btn_refresh = nullptr;
    HWND list_messages = nullptr;
    HWND edit_message = nullptr;
    HWND status = nullptr;

    HFONT font_base = nullptr;
    HFONT font_bold = nullptr;
    HBRUSH brush_bg = nullptr;
    HBRUSH brush_panel = nullptr;
    HBRUSH brush_header = nullptr;
    HBRUSH brush_status = nullptr;
    HBRUSH brush_control = nullptr;

    std::vector<Account> accounts;
    std::vector<MessageSummary> messages;
    std::string current_email;
    std::string current_password;
    std::string current_token;
};

std::wstring w(const std::string& text) {
    return utf8ToWide(text);
}

void setTextUtf8(HWND hwnd, const std::string& text) {
    std::wstring wide = w(text);
    SetWindowTextW(hwnd, wide.c_str());
}

std::string accountStatusTag(const std::string& status) {
    if (status == "registered") {
        return " [REG]";
    }
    if (status == "plus") {
        return " [PLUS]";
    }
    if (status == "banned") {
        return " [BANNED]";
    }
    if (status == "invalid_password") {
        return " [BAD PASS]";
    }
    return {};
}

std::string accountDisplayLine(const Account& acc) {
    return acc.email + accountStatusTag(acc.status);
}

std::string messageTimeLabel(const std::string& created_at) {
    if (created_at.size() >= 19 && created_at[10] == 'T') {
        return created_at.substr(11, 8);
    }
    return created_at;
}

std::string messageDisplayLine(const MessageSummary& msg) {
    std::ostringstream out;
    out << msg.sender << " | " << msg.subject << " | " << messageTimeLabel(msg.created_at);
    return out.str();
}

void setStatus(GuiState* state, const std::string& text) {
    setTextUtf8(state->status, text);
}

void setMessageViewText(GuiState* state, const std::string& text) {
    setTextUtf8(state->edit_message, text);
}

void clearMessageList(GuiState* state) {
    state->messages.clear();
    SendMessageW(state->list_messages, LB_RESETCONTENT, 0, 0);
}

void renderMessageList(GuiState* state) {
    SendMessageW(state->list_messages, LB_RESETCONTENT, 0, 0);
    for (const auto& msg : state->messages) {
        std::wstring line = w(messageDisplayLine(msg));
        SendMessageW(state->list_messages, LB_ADDSTRING, 0, reinterpret_cast<LPARAM>(line.c_str()));
    }
}

void loadAccountsIntoUi(GuiState* state, bool show_status = true) {
    int prev_selection = static_cast<int>(SendMessageW(state->list_accounts, LB_GETCURSEL, 0, 0));
    std::string prev_email;
    if (prev_selection >= 0 && prev_selection < static_cast<int>(state->accounts.size())) {
        prev_email = state->accounts[static_cast<size_t>(prev_selection)].email;
    }

    bool needs_rewrite = false;
    state->accounts = loadAccounts(&needs_rewrite);
    if (needs_rewrite) {
        saveAccounts(state->accounts);
    }

    SendMessageW(state->list_accounts, LB_RESETCONTENT, 0, 0);
    int new_selection = -1;
    for (size_t i = 0; i < state->accounts.size(); ++i) {
        std::wstring line = w(accountDisplayLine(state->accounts[i]));
        SendMessageW(state->list_accounts, LB_ADDSTRING, 0, reinterpret_cast<LPARAM>(line.c_str()));
        if (!prev_email.empty() && state->accounts[i].email == prev_email) {
            new_selection = static_cast<int>(i);
        }
    }

    if (new_selection >= 0) {
        SendMessageW(state->list_accounts, LB_SETCURSEL, static_cast<WPARAM>(new_selection), 0);
    }

    if (show_status) {
        std::ostringstream status;
        status << "Загружено аккаунтов: " << state->accounts.size();
        if (needs_rewrite) {
            status << " (legacy формат конвертирован)";
        }
        setStatus(state, status.str());
    }
}

bool copyToClipboard(HWND owner, const std::string& text) {
    std::wstring wide = w(text);
    if (!OpenClipboard(owner)) {
        return false;
    }
    EmptyClipboard();
    const size_t bytes = (wide.size() + 1) * sizeof(wchar_t);
    HGLOBAL memory = GlobalAlloc(GMEM_MOVEABLE, bytes);
    if (memory == nullptr) {
        CloseClipboard();
        return false;
    }
    void* ptr = GlobalLock(memory);
    if (ptr == nullptr) {
        GlobalFree(memory);
        CloseClipboard();
        return false;
    }
    std::memcpy(ptr, wide.c_str(), bytes);
    GlobalUnlock(memory);
    if (SetClipboardData(CF_UNICODETEXT, memory) == nullptr) {
        GlobalFree(memory);
        CloseClipboard();
        return false;
    }
    CloseClipboard();
    return true;
}

std::string statusLabelRu(const std::string& status) {
    if (status == "registered") {
        return "registered";
    }
    if (status == "plus") {
        return "plus";
    }
    if (status == "banned") {
        return "banned";
    }
    if (status == "invalid_password") {
        return "invalid_password";
    }
    return "not_registered";
}

std::string fullAccountLine(const Account& acc) {
    std::string pass_openai = trim(acc.password_openai);
    std::string pass_mail = trim(acc.password_mail);

    if (pass_openai.empty()) {
        pass_openai = pass_mail;
    }
    if (pass_mail.empty()) {
        pass_mail = pass_openai;
    }

    std::ostringstream line;
    line << acc.email << ":";
    if (!pass_openai.empty() && !pass_mail.empty() && pass_openai != pass_mail) {
        line << pass_openai << ";" << pass_mail;
    } else {
        line << pass_openai;
    }
    return line.str();
}

bool getSelectedAccount(const GuiState* state, Account* out) {
    const int idx = static_cast<int>(SendMessageW(state->list_accounts, LB_GETCURSEL, 0, 0));
    if (idx < 0 || idx >= static_cast<int>(state->accounts.size())) {
        return false;
    }
    *out = state->accounts[static_cast<size_t>(idx)];
    return true;
}

void copySelectedAccountFull(HWND owner, GuiState* state) {
    Account selected;
    if (!getSelectedAccount(state, &selected)) {
        setStatus(state, "Выберите аккаунт");
        return;
    }

    const std::string payload = fullAccountLine(selected);
    if (copyToClipboard(owner, payload)) {
        setStatus(state, "Скопирован полный аккаунт: " + selected.email);
    } else {
        setStatus(state, "Не удалось скопировать полный аккаунт");
    }
}

bool createAccountsSnapshot(const std::vector<Account>& accounts,
                            std::string* out_path,
                            std::string* out_error) {
    std::error_code ec;
    fs::create_directories("backups", ec);
    if (ec) {
        if (out_error != nullptr) {
            *out_error = "create_directories failed";
        }
        return false;
    }

    const std::time_t now = std::time(nullptr);
    std::tm local_tm{};
    localtime_s(&local_tm, &now);

    char timestamp[32]{};
    if (std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", &local_tm) == 0) {
        if (out_error != nullptr) {
            *out_error = "strftime failed";
        }
        return false;
    }

    fs::path snapshot_path = fs::path("backups") / ("accounts_" + std::string(timestamp) + ".txt");
    std::ofstream out(snapshot_path, std::ios::trunc);
    if (!out.is_open()) {
        if (out_error != nullptr) {
            *out_error = "cannot open snapshot file";
        }
        return false;
    }

    for (const auto& acc : accounts) {
        out << acc.email << " / " << serializePasswords(acc) << " / " << statusLabelRu(acc.status) << "\n";
    }

    out.flush();
    if (!out.good()) {
        if (out_error != nullptr) {
            *out_error = "write failed";
        }
        return false;
    }

    if (out_path != nullptr) {
        *out_path = snapshot_path.string();
    }
    return true;
}

void showAnalyticsReport(GuiState* state) {
    if (state->accounts.empty()) {
        setMessageViewText(state, "Нет аккаунтов для аналитики.");
        setStatus(state, "Аналитика: аккаунты отсутствуют");
        return;
    }

    std::map<std::string, size_t> status_counts{
        {"not_registered", 0},
        {"registered", 0},
        {"plus", 0},
        {"banned", 0},
        {"invalid_password", 0},
    };
    std::map<std::string, size_t> domain_counts;
    size_t split_passwords = 0;

    for (const auto& acc : state->accounts) {
        const std::string status_key = statusLabelRu(acc.status);
        status_counts[status_key] += 1;

        std::string domain = extractDomain(acc.email);
        if (!domain.empty()) {
            domain_counts[domain] += 1;
        }

        if (!acc.password_openai.empty() &&
            !acc.password_mail.empty() &&
            acc.password_openai != acc.password_mail) {
            split_passwords += 1;
        }
    }

    std::vector<std::pair<std::string, size_t>> ranked_domains(domain_counts.begin(), domain_counts.end());
    std::sort(
        ranked_domains.begin(),
        ranked_domains.end(),
        [](const auto& lhs, const auto& rhs) {
            if (lhs.second != rhs.second) {
                return lhs.second > rhs.second;
            }
            return lhs.first < rhs.first;
        });

    std::ostringstream report;
    report << "UNIQUE SYSTEM: C++ Account Intelligence\r\n";
    report << "==================================================\r\n";
    report << "Всего аккаунтов: " << state->accounts.size() << "\r\n";
    report << "Раздельные пароли OpenAI/Mail: " << split_passwords << "\r\n\r\n";
    report << "Статусы:\r\n";
    report << " - not_registered: " << status_counts["not_registered"] << "\r\n";
    report << " - registered: " << status_counts["registered"] << "\r\n";
    report << " - plus: " << status_counts["plus"] << "\r\n";
    report << " - banned: " << status_counts["banned"] << "\r\n";
    report << " - invalid_password: " << status_counts["invalid_password"] << "\r\n\r\n";
    report << "Топ доменов:\r\n";

    if (ranked_domains.empty()) {
        report << " (нет данных)\r\n";
    } else {
        const size_t limit = std::min<size_t>(5, ranked_domains.size());
        for (size_t i = 0; i < limit; ++i) {
            report << " " << (i + 1) << ". " << ranked_domains[i].first << " - " << ranked_domains[i].second << "\r\n";
        }
    }

    setMessageViewText(state, report.str());
    setStatus(state, "Аналитика C++ обновлена");
}

void runSnapshotSystem(GuiState* state) {
    std::string path;
    std::string error;
    if (!createAccountsSnapshot(state->accounts, &path, &error)) {
        setStatus(state, "Снапшот не создан: " + error);
        return;
    }
    setStatus(state, "Снапшот сохранен: " + path);
}

void layoutControls(GuiState* state) {
    RECT rc{};
    GetClientRect(state->hwnd, &rc);

    const int width = rc.right - rc.left;
    const int height = rc.bottom - rc.top;

    const int status_h = 30;
    const int top_h = 54;
    const int left_panel_w = 320;
    const int margin = 12;
    const int gap = 8;

    const int content_h = std::max(200, height - status_h);
    const int right_x = left_panel_w + margin;
    const int right_w = std::max(300, width - right_x - margin);

    MoveWindow(state->title, margin, 14, left_panel_w - 2 * margin, 28, TRUE);
    MoveWindow(state->btn_create, margin, 48, left_panel_w - 2 * margin, 32, TRUE);

    const int btn_w = (left_panel_w - 2 * margin - gap) / 2;
    const int btn_row1_y = 88;
    const int btn_row2_y = 126;
    const int btn_row3_y = 164;
    MoveWindow(state->btn_reload, margin, btn_row1_y, btn_w, 30, TRUE);
    MoveWindow(state->btn_copy_email, margin + btn_w + gap, btn_row1_y, btn_w, 30, TRUE);
    MoveWindow(state->btn_copy_full, margin, btn_row2_y, btn_w, 30, TRUE);
    MoveWindow(state->btn_backup, margin + btn_w + gap, btn_row2_y, btn_w, 30, TRUE);
    MoveWindow(state->btn_analytics, margin, btn_row3_y, left_panel_w - 2 * margin, 30, TRUE);

    const int account_list_y = 202;
    const int account_list_h = std::max(120, content_h - account_list_y - margin);
    MoveWindow(state->list_accounts, margin, account_list_y, left_panel_w - 2 * margin, account_list_h, TRUE);

    MoveWindow(state->label_email, right_x, 14, right_w - 108, 28, TRUE);
    MoveWindow(state->btn_refresh, right_x + right_w - 100, 12, 100, 32, TRUE);

    const int messages_y = top_h;
    const int messages_h = std::max(140, (content_h - messages_y - margin - 16) / 2);
    MoveWindow(state->list_messages, right_x, messages_y, right_w, messages_h, TRUE);

    const int message_text_y = messages_y + messages_h + 10;
    const int message_text_h = std::max(120, content_h - message_text_y - margin);
    MoveWindow(state->edit_message, right_x, message_text_y, right_w, message_text_h, TRUE);

    MoveWindow(state->status, 0, height - status_h, width, status_h, TRUE);
}

void requestInboxForSelection(GuiState* state) {
    const int idx = static_cast<int>(SendMessageW(state->list_accounts, LB_GETCURSEL, 0, 0));
    if (idx < 0 || idx >= static_cast<int>(state->accounts.size())) {
        return;
    }

    const Account acc = state->accounts[static_cast<size_t>(idx)];
    std::string password = acc.password_mail.empty() ? acc.password_openai : acc.password_mail;
    if (acc.email.empty() || password.empty()) {
        setStatus(state, "У аккаунта отсутствует email или пароль");
        return;
    }

    state->current_email = acc.email;
    state->current_password = password;
    setTextUtf8(state->label_email, acc.email);
    clearMessageList(state);
    setMessageViewText(state, "Загрузка писем...");
    setStatus(state, "Авторизация и загрузка inbox...");

    HWND hwnd = state->hwnd;
    std::thread([hwnd, email = acc.email, password]() {
        auto* result = new GuiInboxResult();
        result->email = email;
        result->password = password;

        // Always try mail.tm API first — domains may not end with "mail.tm"
        // (e.g. dollicons.com) and the cached domain list may fail to load.
        {
            std::string error;
            auto token_opt = getToken(email, password, &error, 8000);
            if (!token_opt.has_value()) {
                result->success = false;
                result->error = "Ошибка входа: " + error;
            } else {
                auto messages_opt = getMessages(*token_opt, &error, 8000);
                if (!messages_opt.has_value()) {
                    result->success = false;
                    result->error = "Ошибка загрузки писем: " + error;
                } else {
                    result->success = true;
                    result->token = *token_opt;
                    result->messages = std::move(*messages_opt);
                }
            }
        }

        if (!PostMessageW(hwnd, WM_APP_INBOX_READY, reinterpret_cast<WPARAM>(result), 0)) {
            delete result;
        }
    }).detach();
}

void requestMessageDetail(GuiState* state) {
    const int idx = static_cast<int>(SendMessageW(state->list_messages, LB_GETCURSEL, 0, 0));
    if (idx < 0 || idx >= static_cast<int>(state->messages.size())) {
        return;
    }
    if (state->current_token.empty()) {
        setStatus(state, "Нет активной сессии");
        return;
    }

    const MessageSummary msg = state->messages[static_cast<size_t>(idx)];
    setMessageViewText(state, "Загрузка сообщения...");
    setStatus(state, "Загрузка выбранного письма...");

    HWND hwnd = state->hwnd;
    std::thread([hwnd, token = state->current_token, msg]() {
        auto* result = new GuiMessageResult();
        std::string error;
        auto detail_opt = getMessageDetail(token, msg.id, &error);
        if (!detail_opt.has_value()) {
            result->success = false;
            result->error = "Ошибка загрузки письма: " + error;
        } else {
            result->success = true;
            result->sender = detail_opt->sender.empty() ? msg.sender : detail_opt->sender;
            result->subject = detail_opt->subject.empty() ? msg.subject : detail_opt->subject;
            if (!detail_opt->text.empty()) {
                result->content = detail_opt->text;
            } else if (!detail_opt->html.empty()) {
                result->content = detail_opt->html;
            } else {
                result->content = "Нет текстового содержимого.";
            }
        }

        if (!PostMessageW(hwnd, WM_APP_MESSAGE_READY, reinterpret_cast<WPARAM>(result), 0)) {
            delete result;
        }
    }).detach();
}

void requestAccountCreate(GuiState* state) {
    EnableWindow(state->btn_create, FALSE);
    SetWindowTextW(state->btn_create, L"Создание...");
    setStatus(state, "Создание нового аккаунта...");

    HWND hwnd = state->hwnd;
    std::thread([hwnd]() {
        auto* result = new GuiCreateResult();

        std::string error;
        auto domains_opt = getDomains(&error);
        if (!domains_opt.has_value() || domains_opt->empty()) {
            result->success = false;
            result->error = "Не удалось получить домены: " + error;
        } else {
            static thread_local std::mt19937_64 rng(
                static_cast<unsigned long long>(
                    std::chrono::high_resolution_clock::now().time_since_epoch().count()) ^
                static_cast<unsigned long long>(std::hash<std::thread::id>{}(std::this_thread::get_id())));
            std::uniform_int_distribution<size_t> dist(0, domains_opt->size() - 1);
            const std::string domain = (*domains_opt)[dist(rng)];

            const std::string username = randomString(10, "abcdefghijklmnopqrstuvwxyz0123456789");
            const std::string password = randomString(12, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789");
            const std::string email = username + "@" + domain;

            if (!createAccount(email, password, &error)) {
                result->success = false;
                result->error = "Регистрация не удалась: " + error;
            } else {
                appendAccount(email, password);
                result->success = true;
                result->account.email = email;
                result->account.password_openai = password;
                result->account.password_mail = password;
                result->account.status = "not_registered";
            }
        }

        if (!PostMessageW(hwnd, WM_APP_CREATE_READY, reinterpret_cast<WPARAM>(result), 0)) {
            delete result;
        }
    }).detach();
}

LRESULT CALLBACK MainWindowProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    auto* state = reinterpret_cast<GuiState*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));

    switch (msg) {
        case WM_NCCREATE: {
            auto* create = reinterpret_cast<CREATESTRUCTW*>(lparam);
            auto* passed_state = reinterpret_cast<GuiState*>(create->lpCreateParams);
            passed_state->hwnd = hwnd;
            SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(passed_state));
            return TRUE;
        }
        case WM_CREATE: {
            state->brush_bg = CreateSolidBrush(COLOR_BG);
            state->brush_panel = CreateSolidBrush(COLOR_PANEL);
            state->brush_header = CreateSolidBrush(COLOR_HEADER);
            state->brush_status = CreateSolidBrush(COLOR_STATUS);
            state->brush_control = CreateSolidBrush(COLOR_CONTROL);

            state->font_base = CreateFontW(
                -16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");
            state->font_bold = CreateFontW(
                -18, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                DEFAULT_PITCH | FF_DONTCARE, L"Segoe UI");

            state->title = CreateWindowExW(
                0, L"STATIC", L"Mail.tm",
                WS_CHILD | WS_VISIBLE, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_TITLE)),
                nullptr, nullptr);
            state->btn_create = CreateWindowExW(
                0, L"BUTTON", L"+ Создать аккаунт",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_CREATE)),
                nullptr, nullptr);
            state->btn_reload = CreateWindowExW(
                0, L"BUTTON", L"Обновить",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_RELOAD)),
                nullptr, nullptr);
            state->btn_copy_email = CreateWindowExW(
                0, L"BUTTON", L"Копировать Email",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_COPY_EMAIL)),
                nullptr, nullptr);
            state->btn_copy_full = CreateWindowExW(
                0, L"BUTTON", L"Полный аккаунт",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_COPY_FULL)),
                nullptr, nullptr);
            state->btn_backup = CreateWindowExW(
                0, L"BUTTON", L"Снапшот",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_BACKUP)),
                nullptr, nullptr);
            state->btn_analytics = CreateWindowExW(
                0, L"BUTTON", L"Уникальная аналитика",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_ANALYTICS)),
                nullptr, nullptr);
            state->list_accounts = CreateWindowExW(
                WS_EX_CLIENTEDGE, L"LISTBOX", L"",
                WS_CHILD | WS_VISIBLE | LBS_NOTIFY | WS_VSCROLL | LBS_NOINTEGRALHEIGHT,
                0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_LIST_ACCOUNTS)),
                nullptr, nullptr);

            state->label_email = CreateWindowExW(
                0, L"STATIC", L"Выберите аккаунт слева",
                WS_CHILD | WS_VISIBLE | SS_LEFTNOWORDWRAP, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_LABEL_EMAIL)),
                nullptr, nullptr);
            state->btn_refresh = CreateWindowExW(
                0, L"BUTTON", L"Обновить",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_BTN_REFRESH)),
                nullptr, nullptr);
            state->list_messages = CreateWindowExW(
                WS_EX_CLIENTEDGE, L"LISTBOX", L"",
                WS_CHILD | WS_VISIBLE | LBS_NOTIFY | WS_VSCROLL | LBS_NOINTEGRALHEIGHT,
                0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_LIST_MESSAGES)),
                nullptr, nullptr);
            state->edit_message = CreateWindowExW(
                WS_EX_CLIENTEDGE, L"EDIT", L"Выберите письмо, чтобы увидеть содержимое.",
                WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_AUTOVSCROLL | ES_MULTILINE | ES_READONLY,
                0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_EDIT_MESSAGE)),
                nullptr, nullptr);
            state->status = CreateWindowExW(
                0, L"STATIC", L"Готово",
                WS_CHILD | WS_VISIBLE | SS_LEFTNOWORDWRAP, 0, 0, 0, 0, hwnd,
                reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_STATUS)),
                nullptr, nullptr);

            SendMessageW(state->title, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_bold), TRUE);
            SendMessageW(state->btn_create, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->btn_reload, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->btn_copy_email, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->btn_copy_full, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->btn_backup, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->btn_analytics, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->list_accounts, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->label_email, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_bold), TRUE);
            SendMessageW(state->btn_refresh, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->list_messages, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->edit_message, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);
            SendMessageW(state->status, WM_SETFONT, reinterpret_cast<WPARAM>(state->font_base), TRUE);

            layoutControls(state);
            loadAccountsIntoUi(state);

            return 0;
        }
        case WM_SIZE:
            if (state != nullptr) {
                layoutControls(state);
            }
            return 0;
        case WM_ERASEBKGND: {
            if (state == nullptr) {
                return DefWindowProcW(hwnd, msg, wparam, lparam);
            }

            HDC hdc = reinterpret_cast<HDC>(wparam);
            RECT rc{};
            GetClientRect(hwnd, &rc);
            FillRect(hdc, &rc, state->brush_bg);

            RECT left = rc;
            left.right = 320;
            FillRect(hdc, &left, state->brush_panel);

            RECT header = rc;
            header.left = 320;
            header.bottom = 54;
            FillRect(hdc, &header, state->brush_header);

            RECT status_rc = rc;
            status_rc.top = rc.bottom - 30;
            FillRect(hdc, &status_rc, state->brush_status);
            return 1;
        }
        case WM_CTLCOLORSTATIC: {
            if (state == nullptr) {
                return DefWindowProcW(hwnd, msg, wparam, lparam);
            }
            HDC hdc = reinterpret_cast<HDC>(wparam);
            HWND control = reinterpret_cast<HWND>(lparam);
            SetBkMode(hdc, TRANSPARENT);

            if (control == state->title) {
                SetTextColor(hdc, COLOR_ACCENT);
                return reinterpret_cast<LRESULT>(state->brush_panel);
            }
            if (control == state->status) {
                SetTextColor(hdc, COLOR_MUTED);
                SetBkColor(hdc, COLOR_STATUS);
                return reinterpret_cast<LRESULT>(state->brush_status);
            }
            if (control == state->label_email) {
                SetTextColor(hdc, COLOR_TEXT);
                return reinterpret_cast<LRESULT>(state->brush_header);
            }

            SetTextColor(hdc, COLOR_TEXT);
            return reinterpret_cast<LRESULT>(state->brush_bg);
        }
        case WM_CTLCOLORLISTBOX:
        case WM_CTLCOLOREDIT: {
            if (state == nullptr) {
                return DefWindowProcW(hwnd, msg, wparam, lparam);
            }
            HDC hdc = reinterpret_cast<HDC>(wparam);
            SetTextColor(hdc, COLOR_TEXT);
            SetBkColor(hdc, COLOR_CONTROL);
            return reinterpret_cast<LRESULT>(state->brush_control);
        }
        case WM_COMMAND: {
            if (state == nullptr) {
                return 0;
            }
            const int id = LOWORD(wparam);
            const int code = HIWORD(wparam);

            if (id == IDC_BTN_CREATE && code == BN_CLICKED) {
                requestAccountCreate(state);
            } else if (id == IDC_BTN_RELOAD && code == BN_CLICKED) {
                loadAccountsIntoUi(state);
            } else if (id == IDC_BTN_COPY_EMAIL && code == BN_CLICKED) {
                Account selected;
                if (!getSelectedAccount(state, &selected)) {
                    setStatus(state, "Выберите аккаунт");
                } else if (copyToClipboard(hwnd, selected.email)) {
                    setStatus(state, "Скопировано: " + selected.email);
                } else {
                    setStatus(state, "Не удалось скопировать email");
                }
            } else if (id == IDC_BTN_COPY_FULL && code == BN_CLICKED) {
                copySelectedAccountFull(hwnd, state);
            } else if (id == IDC_BTN_BACKUP && code == BN_CLICKED) {
                runSnapshotSystem(state);
            } else if (id == IDC_BTN_ANALYTICS && code == BN_CLICKED) {
                showAnalyticsReport(state);
            } else if (id == IDC_BTN_REFRESH && code == BN_CLICKED) {
                requestInboxForSelection(state);
            } else if (id == IDC_LIST_ACCOUNTS && code == LBN_SELCHANGE) {
                requestInboxForSelection(state);
            } else if (id == IDC_LIST_MESSAGES && code == LBN_SELCHANGE) {
                requestMessageDetail(state);
            }
            return 0;
        }
        case WM_APP_INBOX_READY: {
            if (state == nullptr) {
                return 0;
            }
            std::unique_ptr<GuiInboxResult> result(reinterpret_cast<GuiInboxResult*>(wparam));
            if (!result->success) {
                state->current_token.clear();
                clearMessageList(state);
                setMessageViewText(state, result->error);
                setStatus(state, result->error);
                return 0;
            }

            state->current_email = result->email;
            state->current_password = result->password;
            state->current_token = result->token;
            state->messages = std::move(result->messages);

            renderMessageList(state);
            if (state->messages.empty()) {
                setMessageViewText(state, "Нет новых писем.");
            } else {
                setMessageViewText(state, "Выберите письмо в списке выше.");
            }

            std::ostringstream status;
            status << "Вход выполнен. Писем: " << state->messages.size();
            setStatus(state, status.str());
            return 0;
        }
        case WM_APP_MESSAGE_READY: {
            if (state == nullptr) {
                return 0;
            }
            std::unique_ptr<GuiMessageResult> result(reinterpret_cast<GuiMessageResult*>(wparam));
            if (!result->success) {
                setMessageViewText(state, result->error);
                setStatus(state, result->error);
                return 0;
            }

            std::ostringstream text;
            text << "От: " << result->sender << "\r\n";
            text << "Тема: " << result->subject << "\r\n";
            text << "--------------------------------------------------\r\n\r\n";
            text << result->content;
            setMessageViewText(state, text.str());

            std::regex code_re(R"(\b(\d{6})\b)");
            std::smatch match;
            if (std::regex_search(result->content, match, code_re) && match.size() >= 2) {
                setStatus(state, "Найден код: " + match[1].str());
            } else {
                setStatus(state, "Письмо загружено");
            }
            return 0;
        }
        case WM_APP_CREATE_READY: {
            if (state == nullptr) {
                return 0;
            }
            std::unique_ptr<GuiCreateResult> result(reinterpret_cast<GuiCreateResult*>(wparam));
            EnableWindow(state->btn_create, TRUE);
            SetWindowTextW(state->btn_create, L"+ Создать аккаунт");

            if (!result->success) {
                setStatus(state, result->error);
                return 0;
            }

            loadAccountsIntoUi(state, false);
            int selected = -1;
            for (size_t i = 0; i < state->accounts.size(); ++i) {
                if (state->accounts[i].email == result->account.email) {
                    selected = static_cast<int>(i);
                    break;
                }
            }
            if (selected >= 0) {
                SendMessageW(state->list_accounts, LB_SETCURSEL, static_cast<WPARAM>(selected), 0);
                requestInboxForSelection(state);
            }
            setStatus(state, "Создан аккаунт: " + result->account.email);
            return 0;
        }
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        case WM_NCDESTROY:
            if (state != nullptr) {
                if (state->font_base != nullptr) {
                    DeleteObject(state->font_base);
                }
                if (state->font_bold != nullptr) {
                    DeleteObject(state->font_bold);
                }
                if (state->brush_bg != nullptr) {
                    DeleteObject(state->brush_bg);
                }
                if (state->brush_panel != nullptr) {
                    DeleteObject(state->brush_panel);
                }
                if (state->brush_header != nullptr) {
                    DeleteObject(state->brush_header);
                }
                if (state->brush_status != nullptr) {
                    DeleteObject(state->brush_status);
                }
                if (state->brush_control != nullptr) {
                    DeleteObject(state->brush_control);
                }
                delete state;
                SetWindowLongPtrW(hwnd, GWLP_USERDATA, 0);
            }
            return 0;
        default:
            return DefWindowProcW(hwnd, msg, wparam, lparam);
    }
}

int runGuiApp() {
    HINSTANCE instance = GetModuleHandleW(nullptr);

    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = MainWindowProc;
    wc.hInstance = instance;
    wc.hCursor = LoadCursorW(nullptr, MAKEINTRESOURCEW(32512));
    wc.hbrBackground = nullptr;
    wc.lpszClassName = L"AutoRegCppMainWindow";

    HICON icon = reinterpret_cast<HICON>(LoadImageW(
        nullptr,
        L"assets\\icon.ico",
        IMAGE_ICON,
        0,
        0,
        LR_LOADFROMFILE | LR_DEFAULTSIZE));
    wc.hIcon = icon;
    wc.hIconSm = icon;

    if (!RegisterClassExW(&wc)) {
        std::cerr << "RegisterClassEx failed.\n";
        return 1;
    }

    auto* state = new GuiState();
    HWND hwnd = CreateWindowExW(
        0,
        wc.lpszClassName,
        L"Mail.tm - Auto Registration (C++)",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        1050,
        680,
        nullptr,
        nullptr,
        instance,
        state);
    if (hwnd == nullptr) {
        delete state;
        std::cerr << "CreateWindowEx failed.\n";
        return 1;
    }

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);

    MSG msg{};
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return static_cast<int>(msg.wParam);
}

int runConsoleApp() {
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);

    std::cout << "auto-reg C++ console client\n";
    while (true) {
        printMenu();
        int choice = promptInt("Select: ", 1, 6, 6);
        switch (choice) {
            case 1:
                handleCreateAccount();
                break;
            case 2:
                handleBatchCreate();
                break;
            case 3:
                handleInbox();
                break;
            case 4:
                handleListAccounts();
                break;
            case 5:
                handleBanCheck();
                break;
            default:
                return 0;
        }
    }
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1) {
        std::string arg = argv[1];
        if (arg == "--cli") {
            return runConsoleApp();
        }
        if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: auto_reg_cpp.exe [--cli]\n";
            std::cout << "  no args : launch native C++ GUI (standalone)\n";
            std::cout << "  --cli   : launch legacy console mode\n";
            return 0;
        }
    }

    HWND console = GetConsoleWindow();
    if (console != nullptr) {
        ShowWindow(console, SW_HIDE);
    }
    return runGuiApp();
}
