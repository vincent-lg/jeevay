"""Screen-reader basic API.

Use it like this:

```python
from jeevay.screen_reader import ScreenReader as SR
SR.setup() # only needed once
SR.output("some text") # speech and braille
SR.speak("some text")
SR.braille("Some text")
```

"""

import accessible_output3.outputs.auto


class ScreenReader:

    """Screen-reader API. No need to instantiate it."""

    engine = None

    @classmethod
    def setup(cls) -> bool:
        """Set up the communication with the current screen reader."""
        if cls.engine is None:
            cls.engine = accessible_output3.outputs.auto.Auto()

    @classmethod
    def output(cls, text: str) -> None:
        """Send text to the screen reader (braille and speech).

        Args:
            text (str): text to send.

        """
        if cls.engine is not None:
            cls.engine.braille(text)
            cls.engine.speak(text)

    @classmethod
    def speak(cls, text: str) -> None:
        """Send text to be spoken by the screen reader.

        Args:
            text (str): text to send.

        """
        if cls.engine is not None:
            cls.engine.speak(text)

    def braille(cls, text: str) -> None:
        """Send text to be brailled by the screen reader.

        Args:
            text (str): text to send.

        """
        if cls.engine is not None:
            cls.engine.braille(text)
