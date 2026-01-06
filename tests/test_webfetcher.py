import json
from unittest.mock import Mock, patch

import pytest
import yaml
from bs4 import BeautifulSoup
from lxml import etree
from pydantic import HttpUrl

from ccrepe.plugins import CrepePlugin, WebFetcher


@pytest.fixture
def sample_html():
    return """
    <html>
        <head><title>Test</title></head>
        <body><h1>Hello</h1><p>World</p></body>
    </html>
    """


@pytest.fixture
def fetcher():
    return WebFetcher(HttpUrl("https://example.com"))


class TestWebFetcher:

    @patch("ccrepe.requests.get")
    def test_fetch_caches_results(self, mock_get, fetcher, sample_html):
        response = Mock()
        response.text = sample_html
        response.raise_for_status = Mock()
        mock_get.return_value = response

        first_soup = fetcher.fetch()
        second_soup = fetcher.fetch()

        assert isinstance(first_soup, BeautifulSoup)
        assert first_soup == second_soup
        mock_get.assert_called_once()

    @patch("ccrepe.requests.get")
    def test_raw_html_returns_content(self, mock_get, fetcher, sample_html):
        response = Mock()
        response.text = sample_html
        response.raise_for_status = Mock()
        mock_get.return_value = response

        html_content = fetcher.raw_html()
        assert html_content == sample_html
        mock_get.assert_called_once()

    def test_html_to_xml_parsing(self, fetcher):
        clean_html = "<html><body></body></html>"
        messy_html = "<div><p>Oops<div>"

        for html_text in (clean_html, messy_html):
            xml_elem = fetcher._html_to_xml(html_text)
            assert isinstance(xml_elem, etree._Element)

    def test_xml_to_dict_conversion(self, fetcher):
        xml_str = '<root attr="x"><child>text</child></root>'
        xml_elem = etree.fromstring(xml_str.encode())
        result = fetcher._xml_to_dict(xml_elem)

        assert result["tag"] == "root"
        assert result["attributes"]["attr"] == "x"
        assert result["children"][0]["tag"] == "child"
        assert result["children"][0]["text"] == "text"

    @patch("ccrepe.requests.get")
    def test_conversion_pipeline(self, mock_get, fetcher, sample_html):
        response = Mock()
        response.text = sample_html
        response.raise_for_status = Mock()
        mock_get.return_value = response

        pretty_xml = fetcher.to_pretty_xml()
        markdown = fetcher.to_markdown()
        json_str = fetcher.to_json()
        yaml_str = fetcher.to_yaml()

        for output in (pretty_xml, markdown, json_str, yaml_str):
            assert isinstance(output, str)

        json_data = json.loads(json_str)
        yaml_data = yaml.safe_load(yaml_str)
        for data in (json_data, yaml_data):
            assert data["tag"] == "html"


class TestCrepePlugin:

    class DummyPlugin(CrepePlugin):
        def lexer(self, soup):
            # returns first paragraph content if available
            p_tag = soup.find("p")
            return p_tag.text if p_tag else ""

    @pytest.fixture
    def plugin(self):
        return self.DummyPlugin(
            name="TestPlugin",
            target=HttpUrl("https://example.com")
        )

    @patch.object(WebFetcher, "fetch")
    def test_fetch_invokes_lexer(self, mock_fetch, plugin):
        mock_soup = Mock(spec=BeautifulSoup)
        mock_fetch.return_value = mock_soup

        result = plugin.fetch()
        assert result == plugin.lexer(mock_soup)

    def test_independent_plugin_instances(self):
        url_a = HttpUrl("https://a.com")
        url_b = HttpUrl("https://b.com")
        plugin_a = self.DummyPlugin(name="PluginA", target=url_a)
        plugin_b = self.DummyPlugin(name="PluginB", target=url_b)

        assert plugin_a.web.url != plugin_b.web.url