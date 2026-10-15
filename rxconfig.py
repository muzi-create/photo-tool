import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin


config = rx.Config(
    app_name="phototool",
    frontend_port=3000,
    backend_port=8000,
    show_built_with_reflex=False,
    plugins=[SitemapPlugin()],
)
