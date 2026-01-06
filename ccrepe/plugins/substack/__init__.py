class SubstackPlugin(CrepePlugin):
    def fetch(self) -> str:
        # get the main article from Substack
        soup = self.web.fetch()
        article = soup.find("article") or soup.body
        # use markdown conversion
        return markdownify.markdownify(str(article), heading_style="ATX")


plugin = SubstackPlugin(
    name="Substack PR",
    target="https://druivenheks.substack.com/p/pattern-recognition-and-consequences",
)
