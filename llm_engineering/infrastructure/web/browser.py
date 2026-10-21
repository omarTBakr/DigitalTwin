import logging
import random
import time
from pathlib import Path
from types import TracebackType

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

from llm_engineering.exceptions import AccessBlockedError, SourceUnavailableError

log = logging.getLogger(__name__)

CHALLENGE_MARKERS = ("Just a moment...", "Verify you are human", "cf-challenge", "challenge-platform")
# browsers' everyday profile folders, which Chrome 136+ won't let automation open
DEFAULT_PROFILE_DIRS = {
    (Path.home() / ".config" / name).resolve()
    for name in (
        "google-chrome",
        "google-chrome-beta",
        "chromium",
        "BraveSoftware/Brave-Browser",
        "BraveSoftware/Brave-Browser-Beta",
    )
}


class Browser:
    """A Chromium-based browser (Chrome, or e.g. Brave via `binary_path`) driven by Selenium, browsing at a
    human pace: random pauses between actions, mouse-wheel scrolling in steps.

    `user_data_dir` (+ `profile_directory`) opens a persistent profile — your logins and cookies are kept
    between runs. A profile can only be used by one browser at a time: close the browser that normally
    uses it first. Selenium Manager downloads the chromedriver matching the browser's version.

    with Browser(source="medium", headless=False, user_data_dir=Path("~/.config/digital-twin-browser")) as b:
        html = b.open("https://...")
    """

    def __init__(
        self,
        *,
        source: str,
        headless: bool = True,
        page_load_timeout_s: float = 30,
        challenge_wait_s: float | None = None,
        binary_path: str | None = None,
        user_data_dir: Path | None = None,
        profile_directory: str | None = None,
        delay_s: tuple[float, float] = (2.0, 5.0),
    ):
        self.source = source
        self.headless = headless
        self.page_load_timeout_s = page_load_timeout_s
        # how long a bot challenge may take to clear (JS checks pass on their own; headed lets you click)
        self.challenge_wait_s = challenge_wait_s if challenge_wait_s is not None else (15 if headless else 30)
        self.binary_path = binary_path
        self.user_data_dir = user_data_dir
        self.profile_directory = profile_directory
        self.delay_s = delay_s
        self._driver: webdriver.Chrome | None = None

    def __enter__(self) -> "Browser":
        options = Options()
        if self.binary_path:
            options.binary_location = self.binary_path
        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir.expanduser()}")
        if self.profile_directory:
            options.add_argument(f"--profile-directory={self.profile_directory}")
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-dev-shm-usage")  # small /dev/shm in containers
        options.add_argument("--window-size=1366,1000")
        try:
            self._driver = webdriver.Chrome(options=options)
        except SessionNotCreatedException as exc:
            raise SourceUnavailableError(
                f"cannot start the browser: {exc.msg}{self._profile_hint()}", source=self.source
            ) from exc
        except WebDriverException as exc:
            raise SourceUnavailableError(f"cannot start the browser: {exc.msg}", source=self.source) from exc
        self._driver.set_page_load_timeout(self.page_load_timeout_s)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> None:
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def _profile_hint(self) -> str:
        if not self.user_data_dir:
            return ""
        if self.user_data_dir.expanduser().resolve() in DEFAULT_PROFILE_DIRS:
            return (
                " — Chrome 136+ refuses automation of its default profile folder (a security measure);"
                " use a separate user_data_dir for the crawler and log in there once"
            )
        return " — is that profile already open? Close the browser using it first."

    @property
    def driver(self) -> webdriver.Chrome:
        if self._driver is None:
            raise RuntimeError("Browser used outside its `with` block")
        return self._driver

    def pause(self) -> None:
        """A random human-scale pause between actions."""
        time.sleep(random.uniform(*self.delay_s))

    def open(self, url: str) -> str:
        """Load a page, pause like a reader would, return its HTML.

        Raises AccessBlockedError if a bot challenge doesn't clear, SourceUnavailableError otherwise.
        """
        try:
            self.driver.get(url)
        except TimeoutException as exc:
            raise SourceUnavailableError(f"timed out loading {url}", source=self.source) from exc
        except WebDriverException as exc:
            raise SourceUnavailableError(f"cannot load {url}: {exc.msg}", source=self.source) from exc
        self.pause()
        html = self.page_source
        if self.is_challenge(html):
            html = self._wait_for_challenge(url)
        return html

    def _wait_for_challenge(self, url: str) -> str:
        """Give an interstitial ("Just a moment...") time to clear, as a person's browser would."""
        log.info("bot challenge at %s; waiting up to %.0fs for it to clear", url, self.challenge_wait_s)
        deadline = time.monotonic() + self.challenge_wait_s
        while time.monotonic() < deadline:
            time.sleep(1)
            html = self.page_source
            if not self.is_challenge(html):
                return html
        hint = "try `headless: false` and click the check" if self.headless else "the check did not clear in the open window"
        raise AccessBlockedError(f"bot challenge at {url} ({hint})", source=self.source)

    def scroll_down(self) -> bool:
        """One mouse-wheel scroll of a few hundred pixels, then a pause. Returns False at the end of the page."""
        try:
            before = self.driver.execute_script("return window.pageYOffset")
            ActionChains(self.driver).scroll_by_amount(0, random.randint(350, 750)).perform()
            self.pause()
            after = self.driver.execute_script("return window.pageYOffset")
        except WebDriverException as exc:
            raise SourceUnavailableError(f"browser closed while scrolling: {exc.msg}", source=self.source) from exc
        return after > before

    @property
    def page_source(self) -> str:
        try:
            return self.driver.page_source
        except WebDriverException as exc:
            raise SourceUnavailableError(f"browser closed: {exc.msg}", source=self.source) from exc

    @staticmethod
    def is_challenge(html: str) -> bool:
        head = html[:20000]
        return any(marker in head for marker in CHALLENGE_MARKERS)
