from pydantic import BaseModel, HttpUrl
from typing import Optional
from abc import ABC
import requests
from bs4 import BeautifulSoup
import markdownify
from lxml import html, etree
import json
import yaml


# wrapper for fetching so we don't repeat this code in each plugin
class WebFetcher:
    def __init__(self, url: HttpUrl):
        self.url = str(url)
        self._html = None
        self._soup = None

    def _html_to_xml(self, html_text: str) -> etree._Element:
        # parse cursed HTML
        parser = html.HTMLParser(
            remove_comments=True,
            remove_pis=True,
            recover=True # don't choke when we get garbage html
        )

        # stringify de htmllen
        doc = html.fromstring(html_text, parser=parser)

        # serialize as well-formed XHTML
        xml_bytes = etree.tostring(
            doc,
            method="xml",
            encoding="utf-8",
            pretty_print=True # ignore the pycharm bint warning what even is a pycharm
        )

        # re-parse as strict XML
        return etree.fromstring(xml_bytes)

    # helper function to support our yaml and json broeren
    def _xml_to_dict(self, elem):
        node = {
            "tag": elem.tag,
            "attributes": dict(elem.attrib)
        }

        text = (elem.text or "").strip()
        if text:
            node["text"] = text

        children = [self._xml_to_dict(c) for c in elem]
        if children:
            node["children"] = children

        return node

    def fetch(self) -> BeautifulSoup:
        # fetches the page if not already fetched
        if self._soup is None:
            resp = requests.get(self.url)
            resp.raise_for_status()
            self._html = resp.text
            self._soup = BeautifulSoup(self._html, "html.parser")
        return self._soup

    def raw_html(self) -> str:
        if self._html is None:
            self.fetch()
        return self._html

    # we are using xml as a transport layer, so we probably are going to want
    # to pull what comes out of fetch(), conform it to xml, and then convert
    # that to markdown.
    def transport_xml(self) -> etree._Element:
        xml = self._html_to_xml(self.raw_html())
        return xml

    # let the base class do the heavy lifting and use xml in the middle.
    # three identical methods, markdown, json, yaml
    def to_markdown(self) -> str:
        return markdownify.markdownify(
            self.to_pretty_xml(),
            heading_style="ATX"
        )

    def to_json(self) -> str:
        xml = self.transport_xml()
        data = self._xml_to_dict(xml)
        return json.dumps(data, indent=2)

    def to_yaml(self) -> str:
        xml = self.transport_xml()
        data = self._xml_to_dict(xml)
        return yaml.safe_dump(data, sort_keys=False)

    def to_pretty_xml(self) -> str:
        xml_bytes = etree.tostring(
            self.transport_xml(),
            pretty_print=True,  # ur a bint u bint don't bint me
            encoding="unicode"  # return str instead of bytes
        )
        return xml_bytes

# base class for plugins
class CrepePlugin(BaseModel, ABC):
    name: str
    target: HttpUrl
    web: WebFetcher
    xml: Optional[etree._Element] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        # each plugin gets its own fetcher
        self.web = WebFetcher(self.target)

    def fetch(self) -> str:
        # base fetch handles network + soup creation
        soup = self.web.fetch()
        # pass the soup to process/lexer method for actual output
        return self.lexer(soup)




