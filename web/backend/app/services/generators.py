import random
from datetime import datetime, timedelta

from faker import Faker

fake_en = Faker("en_US")
fake_in = Faker("en_IN")
fake_kr = Faker("ko_KR")


def random_person() -> dict[str, str]:
    name = fake_en.first_name()
    start_date = datetime(1975, 1, 1)
    end_date = datetime(2004, 12, 31)
    days_between = (end_date - start_date).days
    birthdate = start_date + timedelta(days=random.randint(0, days_between))
    return {
        "name": name,
        "birthdate": birthdate.strftime("%d.%m.%Y"),
    }


def _generate_luhn_card(prefix: str, extra_digits: int) -> str:
    digits = [int(ch) for ch in prefix]
    for _ in range(extra_digits):
        digits.append(random.randint(0, 9))

    checksum = 0
    for idx, value in enumerate(digits):
        if idx % 2 == 0:
            doubled = value * 2
            if doubled > 9:
                doubled -= 9
            checksum += doubled
        else:
            checksum += value

    check_digit = (10 - (checksum % 10)) % 10
    return "".join(map(str, digits)) + str(check_digit)


def _future_expiry() -> str:
    month = random.randint(1, 12)
    year = datetime.now().year + random.randint(1, 5)
    return f"{month:02d}/{str(year)[-2:]}"


def _cvv() -> str:
    return f"{random.randint(100, 999)}"


def generator_in() -> dict[str, str]:
    cities = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata"]
    areas = ["Andheri", "Bandra", "Connaught Place", "Koramangala", "Jubilee Hills"]
    streets = ["MG Road", "Park Street", "Brigade Road", "Anna Salai", "FC Road"]

    city = random.choice(cities)
    area = random.choice(areas)
    street = random.choice(streets)

    return {
        "card": _generate_luhn_card("55182706", 7),
        "exp": _future_expiry(),
        "cvv": _cvv(),
        "name": fake_in.name(),
        "city": fake_in.city(),
        "street": f"{fake_in.street_name()} {fake_in.building_number()}",
        "postcode": fake_in.postcode(),
        "address_en": f"{random.randint(1, 999)}, {street}, {area}, {city}, India",
    }


def generator_sk() -> dict[str, str]:
    districts = ["Gangnam-gu", "Mapo-gu", "Yongsan-gu", "Seocho-gu", "Songpa-gu"]
    streets = ["Teheran-ro", "Hakdong-ro", "Olympic-ro", "Hangang-daero", "Sejong-daero"]

    return {
        "card": _generate_luhn_card("6258142602", 5),
        "exp": _future_expiry(),
        "cvv": _cvv(),
        "name": fake_kr.name(),
        "city": "Seoul",
        "street": f"{fake_kr.street_name()} {fake_kr.building_number()}",
        "postcode": fake_kr.postcode(),
        "address_en": f"{random.randint(1, 999)}, {random.choice(streets)}, {random.choice(districts)}, Seoul, Republic of Korea",
    }
