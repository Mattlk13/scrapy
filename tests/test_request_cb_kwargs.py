from testfixtures import LogCapture
from twisted.internet.defer import inlineCallbacks

from scrapy.http import Request
from scrapy.utils.test import get_crawler
from tests.mockserver.http import MockServer
from tests.spiders import MockServerSpider


class InjectArgumentsDownloaderMiddleware:
    """
    Make sure downloader middlewares are able to update the keyword arguments
    """

    def process_request(self, request, spider):
        if request.callback.__name__ == "parse_downloader_mw":
            request.cb_kwargs["from_process_request"] = True

    def process_response(self, request, response, spider):
        if request.callback.__name__ == "parse_downloader_mw":
            request.cb_kwargs["from_process_response"] = True
        return response


class InjectArgumentsSpiderMiddleware:
    """
    Make sure spider middlewares are able to update the keyword arguments
    """

    async def process_start(self, start):
        async for request in start:
            if request.callback.__name__ == "parse_spider_mw":
                request.cb_kwargs["from_process_start"] = True
            yield request

    def process_spider_input(self, response, spider):
        request = response.request
        if request.callback.__name__ == "parse_spider_mw":
            request.cb_kwargs["from_process_spider_input"] = True

    def process_spider_output(self, response, result, spider):
        for element in result:
            if (
                isinstance(element, Request)
                and element.callback.__name__ == "parse_spider_mw_2"
            ):
                element.cb_kwargs["from_process_spider_output"] = True
            yield element


class KeywordArgumentsSpider(MockServerSpider):
    name = "kwargs"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            InjectArgumentsDownloaderMiddleware: 750,
        },
        "SPIDER_MIDDLEWARES": {
            InjectArgumentsSpiderMiddleware: 750,
        },
    }

    checks: list[bool] = []

    async def start(self):
        data = {"key": "value", "number": 123, "callback": "some_callback"}
        yield Request(self.mockserver.url("/first"), self.parse_first, cb_kwargs=data)
        yield Request(
            self.mockserver.url("/general_with"), self.parse_general, cb_kwargs=data
        )
        yield Request(self.mockserver.url("/general_without"), self.parse_general)
        yield Request(self.mockserver.url("/no_kwargs"), self.parse_no_kwargs)
        yield Request(
            self.mockserver.url("/default"), self.parse_default, cb_kwargs=data
        )
        yield Request(
            self.mockserver.url("/takes_less"), self.parse_takes_less, cb_kwargs=data
        )
        yield Request(
            self.mockserver.url("/takes_more"), self.parse_takes_more, cb_kwargs=data
        )
        yield Request(self.mockserver.url("/downloader_mw"), self.parse_downloader_mw)
        yield Request(self.mockserver.url("/spider_mw"), self.parse_spider_mw)

    def parse_first(self, response, key, number):
        self.checks.append(key == "value")
        self.checks.append(number == 123)
        self.crawler.stats.inc_value("boolean_checks", 2)
        yield response.follow(
            self.mockserver.url("/two"),
            self.parse_second,
            cb_kwargs={"new_key": "new_value"},
        )

    def parse_second(self, response, new_key):
        self.checks.append(new_key == "new_value")
        self.crawler.stats.inc_value("boolean_checks")

    def parse_general(self, response, **kwargs):
        if response.url.endswith("/general_with"):
            self.checks.append(kwargs["key"] == "value")
            self.checks.append(kwargs["number"] == 123)
            self.checks.append(kwargs["callback"] == "some_callback")
            self.crawler.stats.inc_value("boolean_checks", 3)
        elif response.url.endswith("/general_without"):
            self.checks.append(
                kwargs == {}  # pylint: disable=use-implicit-booleaness-not-comparison
            )
            self.crawler.stats.inc_value("boolean_checks")

    def parse_no_kwargs(self, response):
        self.checks.append(response.url.endswith("/no_kwargs"))
        self.crawler.stats.inc_value("boolean_checks")

    def parse_default(self, response, key, number=None, default=99):
        self.checks.append(response.url.endswith("/default"))
        self.checks.append(key == "value")
        self.checks.append(number == 123)
        self.checks.append(default == 99)
        self.crawler.stats.inc_value("boolean_checks", 4)

    def parse_takes_less(self, response, key, callback):
        """
        Should raise
        TypeError: parse_takes_less() got an unexpected keyword argument 'number'
        """

    def parse_takes_more(self, response, key, number, callback, other):
        """
        Should raise
        TypeError: parse_takes_more() missing 1 required positional argument: 'other'
        """

    def parse_downloader_mw(
        self, response, from_process_request, from_process_response
    ):
        self.checks.append(bool(from_process_request))
        self.checks.append(bool(from_process_response))
        self.crawler.stats.inc_value("boolean_checks", 2)

    def parse_spider_mw(self, response, from_process_spider_input, from_process_start):
        self.checks.append(bool(from_process_spider_input))
        self.checks.append(bool(from_process_start))
        self.crawler.stats.inc_value("boolean_checks", 2)
        return Request(self.mockserver.url("/spider_mw_2"), self.parse_spider_mw_2)

    def parse_spider_mw_2(self, response, from_process_spider_output):
        self.checks.append(bool(from_process_spider_output))
        self.crawler.stats.inc_value("boolean_checks", 1)


class TestCallbackKeywordArguments:
    @classmethod
    def setup_class(cls):
        cls.mockserver = MockServer()
        cls.mockserver.__enter__()

    @classmethod
    def teardown_class(cls):
        cls.mockserver.__exit__(None, None, None)

    @inlineCallbacks
    def test_callback_kwargs(self):
        crawler = get_crawler(KeywordArgumentsSpider)
        with LogCapture() as log:
            yield crawler.crawl(mockserver=self.mockserver)
        assert all(crawler.spider.checks)
        assert len(crawler.spider.checks) == crawler.stats.get_value("boolean_checks")
        # check exceptions for argument mismatch
        exceptions = {}
        for line in log.records:
            for key in ("takes_less", "takes_more"):
                if key in line.getMessage():
                    exceptions[key] = line
        assert exceptions["takes_less"].exc_info[0] is TypeError
        assert str(exceptions["takes_less"].exc_info[1]).endswith(
            "parse_takes_less() got an unexpected keyword argument 'number'"
        ), "Exception message: " + str(exceptions["takes_less"].exc_info[1])
        assert exceptions["takes_more"].exc_info[0] is TypeError
        assert str(exceptions["takes_more"].exc_info[1]).endswith(
            "parse_takes_more() missing 1 required positional argument: 'other'"
        ), "Exception message: " + str(exceptions["takes_more"].exc_info[1])
