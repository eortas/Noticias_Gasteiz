from api.extract import extract_images


def test_extract_images_supports_picture_and_lazy_loading():
    html = """
    <html><body><article>
        <picture>
            <source data-srcset="/small.webp 400w, /large.webp 1200w">
            <img src="data:image/gif;base64,placeholder" alt="Foto principal">
        </picture>
        <img data-lazy-src="images/second.jpg" alt="Segunda foto">
    </article></body></html>
    """

    images = extract_images(html, "https://example.com/news/article")

    assert images == [
        {"url": "https://example.com/large.webp", "alt": "Foto principal"},
        {"url": "https://example.com/news/images/second.jpg", "alt": "Segunda foto"},
    ]


def test_extract_images_uses_open_graph_as_fallback():
    html = '<html><head><meta property="og:image" content="/cover.jpg"></head><body></body></html>'

    images = extract_images(html, "https://example.com/article")

    assert images == [{"url": "https://example.com/cover.jpg", "alt": ""}]
