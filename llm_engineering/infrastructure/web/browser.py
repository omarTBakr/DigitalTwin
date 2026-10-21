import logging
import time
from types import TracebackType

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

from llm_engineering.exceptions import AccessBlockedError, SourceUnavailableError

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
CHALLENGE_MARKERS = ("Just a moment...", "Verify you are human", "cf-challenge", "challenge-platform")


class Browser:
    """Chrome via Selenium, as a context manager. Selenium Manager downloads the matching driver.

    with Browser(source="medium", headless=True) as browser:
        html = browser.open("https://...")
    """

    def __init__(self, *, source: str, headless: bool = True, page_load_timeout_s: float = 30):
        self.source = source
        self.headless = headless
        self.page_load_timeout_s = page_load_timeout_s
        self._driver: webdriver.Chrome | None = None

    def __enter__(self) -> "Browser":
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1366,2000")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        try:
            self._driver = webdriver.Chrome(options=options)
        except WebDriverException as exc:
            raise SourceUnavailableError(f"cannot start Chrome: {exc.msg}", source=self.source) from exc
        self._driver.set_page_load_timeout(self.page_load_timeout_s)
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    @property
    def driver(self) -> webdriver.Chrome:
        if self._driver is None:
            raise RuntimeError("Browser used outside its `with` block")
        return self._driver

    def open(self, url: str) -> str:
        """Load a page and return its HTML. Raises AccessBlockedError on a bot challenge, SourceUnavailableError otherwise."""
        try:
            self.driver.get(url)
        except TimeoutException as exc:
            raise SourceUnavailableError(f"timed out loading {url}", source=self.source) from exc
        except WebDriverException as exc:
            raise SourceUnavailableError(f"cannot load {url}: {exc.msg}", source=self.source) from exc
        html = self.driver.page_source
        if self.is_challenge(html):
            raise AccessBlockedError(
                f"bot challenge at {url}; try `headless: false` in the source config", source=self.source
            )
        return html

    def scroll_to_bottom(self, pause_s: float) -> bool:
        """Scroll once; returns False when the page height stopped growing (end of infinite scroll)."""
        before = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_s)
        after = self.driver.execute_script("return document.body.scrollHeight")
        return after > before

    @property
    def page_source(self) -> str:
        return self.driver.page_source

    @staticmethod
    def is_challenge(html: str) -> bool:
        head = html[:20000]
        return any(marker in head for marker in CHALLENGE_MARKERS)
