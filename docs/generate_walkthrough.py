from pathlib import Path
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "docs" / "video-output"
FINAL_VIDEO = ROOT / "docs" / "repoarena-walkthrough.mp4"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def set_caption(page, title, detail):
    page.evaluate(
        """([title, detail]) => {
          let card = document.querySelector('#walkthrough-caption');
          if (!card) {
            card = document.createElement('div');
            card.id = 'walkthrough-caption';
            card.style.cssText = `
              position: fixed; left: 50%; bottom: 24px; z-index: 9999;
              transform: translateX(-50%); width: min(760px, calc(100vw - 48px));
              padding: 15px 20px; border: 1px solid #a9b17f; border-radius: 12px;
              background: rgba(255, 253, 247, .96); color: #27311f;
              box-shadow: 0 16px 50px rgba(54, 61, 36, .22);
              font: 14px/1.45 Inter, ui-sans-serif, system-ui, sans-serif;
            `;
            document.body.append(card);
          }
          card.replaceChildren();
          const heading = document.createElement('strong');
          heading.textContent = title;
          heading.style.display = 'block';
          heading.style.color = '#566731';
          heading.style.fontSize = '16px';
          heading.style.marginBottom = '3px';
          const copy = document.createElement('span');
          copy.textContent = detail;
          card.append(heading, copy);
        }""",
        [title, detail],
    )


def main():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for old_video in VIDEO_DIR.glob("*.webm"):
        old_video.unlink()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(EDGE), headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1440, "height": 900},
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        set_caption(page, "RepoArena walkthrough", "Turn an engineering issue into two proposals, a critique, and an inspectable verdict.")
        page.wait_for_timeout(2600)

        set_caption(page, "1. Start with a challenge", "Use your own engineering problem, or load the included example to explore the workflow.")
        page.get_by_role("button", name="Try an example").click()
        page.wait_for_timeout(2200)

        set_caption(page, "2. Choose how to run", "Live Ollama keeps inference local. This machine has qwen2.5:3b ready to use.")
        page.get_by_role("button", name="Live Ollama").click()
        page.wait_for_timeout(2500)

        set_caption(page, "3. Use Sample replay for a quick tour", "A live run makes four model calls. The curated sample shows the complete interface in seconds.")
        page.get_by_role("button", name="Sample replay").click()
        page.wait_for_timeout(1800)

        set_caption(page, "4. Enter the arena", "RepoArena runs Builder A, Builder B, the skeptic, and the judge as separate stages.")
        page.get_by_role("button", name="Enter the arena").click()
        page.locator("#verdict-card").wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(1200)

        set_caption(page, "5. Compare independent proposals", "The two builders start independently, making their assumptions and tradeoffs easier to compare.")
        page.locator(".candidate-grid").scroll_into_view_if_needed()
        page.wait_for_timeout(3000)

        set_caption(page, "6. Review the stress test", "The skeptic highlights failure modes and recommends concrete tests for both designs.")
        page.locator("#critique-card").scroll_into_view_if_needed()
        page.wait_for_timeout(3000)

        set_caption(page, "7. Inspect the verdict", "The harness calculates weighted scores for correctness, security, and testability.")
        page.locator("#verdict-card").scroll_into_view_if_needed()
        page.wait_for_timeout(3500)

        set_caption(page, "8. Export the evidence", "Download the session to preserve prompts, raw responses, validated results, scores, and timing.")
        page.wait_for_timeout(3000)

        set_caption(page, "Ready to challenge an idea?", "Open RepoArena locally at 127.0.0.1:8000 and switch to Live Ollama when you want a fresh debate.")
        page.wait_for_timeout(3000)

        video = page.video
        context.close()
        browser.close()
        source_video = Path(video.path())

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(source_video),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(FINAL_VIDEO),
        ],
        check=True,
    )
    print(FINAL_VIDEO)


if __name__ == "__main__":
    main()
