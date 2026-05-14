import re
import urllib.request

url = "https://berekekans.kg/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

out = r"c:\Users\User\Desktop\portfolio_django\tmp_bereke.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
print("og:", m.group(1) if m else "none")
# hero carousel images often in static
for pat in [
    r'src="(https://[^"]+\.(?:jpg|jpeg|png|webp))"',
    r"url\(['\"]?(https://[^'\")]+\.(?:jpg|jpeg|png|webp))",
]:
    found = re.findall(pat, html, re.I)
    print("sample urls", found[:5])
    if found:
        break
