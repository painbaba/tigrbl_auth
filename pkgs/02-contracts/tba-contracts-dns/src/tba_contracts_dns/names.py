import idna


def normalize_domain(domain: str) -> str:
    try:
        return idna.encode(
            domain.removesuffix("."), uts46=True, std3_rules=True
        ).decode()
    except (idna.IDNAError, UnicodeError) as exc:
        raise ValueError("invalid DNS domain") from exc
