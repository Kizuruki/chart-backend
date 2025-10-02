import urllib.parse


def url_creator(base: str, *args, as_sonolus_open: bool = False) -> str:
    path = "/".join(args)

    if base.endswith("/"):
        url = base + path
    else:
        url = base + "/" + path

    if as_sonolus_open:
        parsed_url = urllib.parse.urlparse(url)
        sonolus_url = f"https://open.sonolus.com/{parsed_url.netloc}{parsed_url.path}"
        return sonolus_url
    return url
