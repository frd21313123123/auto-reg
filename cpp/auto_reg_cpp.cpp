#include <windows.h>
#include <winhttp.h>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <random>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

namespace {

constexpr const char* kApiBase = "https://api.mail.tm";
constexpr const char* kAccountsFile = "accounts.txt";

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

HttpResponse httpRequest(const std::wstring& method,
                         const std::wstring& url,
                         const std::string& body = {},
                         const std::vector<std::wstring>& headers = {}) {
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

    WinHttpSetTimeouts(session.handle, 12000, 12000, 12000, 18000);

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
    static std::mt19937_64 rng(
        static_cast<unsigned long long>(
            std::chrono::high_resolution_clock::now().time_since_epoch().count()));
    std::uniform_int_distribution<size_t> dist(0, alphabet.size() - 1);
    std::string out;
    out.reserve(len);
    for (size_t i = 0; i < len; ++i) {
        out.push_back(alphabet[dist(rng)]);
    }
    return out;
}

std::optional<std::vector<std::string>> getDomains(std::string* error) {
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/domains?page=1");
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
                                    std::string* error) {
    std::ostringstream body;
    body << "{\"address\":\"" << jsonEscape(email) << "\",\"password\":\"" << jsonEscape(password) << "\"}";

    std::vector<std::wstring> headers{
        L"Content-Type: application/json",
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/token");
    HttpResponse res = httpRequest(L"POST", url, body.str(), headers);

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

std::optional<std::vector<MessageSummary>> getMessages(const std::string& token, std::string* error) {
    std::vector<std::wstring> headers{
        utf8ToWide(std::string("Authorization: Bearer ") + token),
        L"Accept: application/ld+json, application/json"};
    const std::wstring url = utf8ToWide(std::string(kApiBase) + "/messages?page=1");
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

void appendAccount(const std::string& email, const std::string& password) {
    std::ofstream out(kAccountsFile, std::ios::app);
    if (!out.is_open()) {
        std::cerr << "Warning: cannot open " << kAccountsFile << " for writing.\n";
        return;
    }
    out << email << " / " << password << ";" << password << " / registered\n";
}

std::string promptLine(const std::string& label, bool allow_empty = false) {
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

void handleInbox() {
    std::string email = promptLine("Email: ");
    std::string password = promptLine("Password: ");

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

void printMenu() {
    std::cout << "\n=== auto-reg C++ (mail.tm) ===\n"
              << "1. Create account\n"
              << "2. Login + read inbox\n"
              << "3. Exit\n";
}

}  // namespace

int main() {
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);

    std::cout << "auto-reg C++ console client\n";
    while (true) {
        printMenu();
        int choice = promptInt("Select: ", 1, 3, 3);
        if (choice == 1) {
            handleCreateAccount();
        } else if (choice == 2) {
            handleInbox();
        } else {
            break;
        }
    }
    return 0;
}
