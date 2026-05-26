# Sketch Studio

A local tool for cleaning hand-drawn sketches and rendering them as AI-generated architectural or design images using [Replicate](https://replicate.com)'s Seedream models. Runs entirely on your machine — no cloud account needed beyond the API key.

![Sketch Studio UI](tests/DSC09933.jpg)

---

## What it does

1. **Upload a sketch** — drag and drop or use the file picker (JPEG, PNG, HEIC supported)
2. **Auto-clean** — the app converts your sketch to a high-contrast black-and-white image using a local pixel-diff algorithm; adjust the threshold slider to taste
3. **Generate** — sends the cleaned sketch to Replicate's Seedream model and streams the result back into the browser
4. **Iterate** — tweak the prompt, modifiers, resolution, or style and regenerate

Optional features:
- **Polish prompt** — rewrites your prompt via Claude Haiku (requires an Anthropic key)
- **Reference images** — drop images into `img_ref/` to guide the style (Seedream 5 Lite only)
- **Color sketch mode** — skip grayscale conversion to preserve coloured sketches

---

## Requirements

- Python 3.6 or later
- A [Replicate API key](https://replicate.com/account/api-tokens)
- *(Optional)* An [Anthropic API key](https://console.anthropic.com/keys) for the "Polish prompt" feature
- *(Optional)* `pillow-heif` + `Pillow` for HEIC file support on non-Windows platforms:
  ```
  pip install pillow-heif Pillow
  ```
  On Windows, HEIC conversion falls back to the built-in `System.Drawing` API automatically.

---

## Setup

1. **Clone the repo**
   ```
   git clone https://github.com/your-username/Sketch-Studio-Public.git
   cd Sketch-Studio-Public
   ```

2. **Add your Replicate API key**

   Open `api_key.txt` and paste your key (one line, no quotes):
   ```
   r8_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. **_(Optional)_ Add your Anthropic API key**

   Open `claude_key.txt` and paste your key:
   ```
   sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## Running

**Windows (recommended):**
```
Launch.bat
```
This kills any existing process on port 8741, starts the server, and opens the app in your default browser.

**Any platform:**
```
python server.py
```
Then open `http://127.0.0.1:8741/sketch_styler.html` in your browser.

---

## Reference images (Seedream 5 Lite)

Drop images into the `img_ref/` folder — they'll appear as a selectable gallery in the UI. Checked images are prepended to the generation input to guide style and composition. The `img_ref/` folder ships with 10 sample reference images to get you started.

---

## Sample sketches

The `tests/` folder contains sample input sketches you can use to try the app straight away.

---

## License

MIT — see [LICENSE](LICENSE).
