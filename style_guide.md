# HTML Slide Style Guide

This document summarizes the rules and style standards to apply when creating presentation `.html` slides based on `MeshTailor_review_slides.md`.

The goals are as follows:

- The overall impression should be `clean`, `technical`, and `editorial`
- The default background should be `white`
- Design accents should rely on `subtle gradient`
- Clear information delivery comes first, and decoration must never interfere with the content

## 1. Overall Direction

### Core Principles
- Because these slides are for a paper presentation, `readability` is the top priority.
- There should be visual accents, but avoid excessive color contrast or heavy backgrounds.
- Each slide should communicate only `one core message`.
- Figures are not just supporting material. They can be central to the explanation and should be treated on par with text.

### Mood
- Minimal layout centered on a white background
- Gray-based text with soft teal/blue gradient accents
- Minimal use of cards, lines, and background blur
- Keep the result closer to a `well-organized research presentation` than a `flashy template`

## 2. Canvas and Layout

### Aspect Ratio
- The default ratio is `16:9`
- The baseline resolution is `1600 x 900` or `1920 x 1080`

### Safe Margins
- Left/right padding: `72-96px`
- Top/bottom padding: `56-72px`
- All text and figures must stay within the safe margins

### Default Layout Rules
- A single slide should use no more than two of the following three areas
- `title area`
- `content area`
- `footer/meta area`
- Avoid overly complex splits; default to `1-column` or `2-column`
- Three or more columns are allowed only for experiment comparison tables or multi-figure slides

### Recommended Structure by Slide Type
- Title slide: centered or top-left aligned with generous whitespace
- Section opener: title plus a one-line message
- General explanation slide: text on the left / figure on the right, or key message on top / figure below
- Results slide: figure-centered, with only 2-4 lines of summary text
- Conclusion slide: reduce sentence count and emphasize the takeaway

## 3. Typography

### Font Direction
- Use sans-serif by default
- Avoid fonts with overly strong personality
- Recommended families:
- `Pretendard`
- `SUIT`
- `Noto Sans KR`
- Prioritize fonts that remain highly readable across English text, numbers, and Korean

### Text Hierarchy
- Slide Title: `34-42px`, `700`
- Section Title: `26-32px`, `700`
- Body: `20-24px`, `400-500`
- Caption / Figure ref / Footer: `14-16px`, `400-500`

### Typography Rules
- Use bullets rather than long paragraphs
- Keep each bullet to `within 2 lines` whenever possible
- Recommend `3-5 bullets` per slide
- Use `bold` for emphasis; do not use underlines
- Default text alignment is `left`
- Only titles may be `center` aligned when appropriate

## 4. Color System

### Base Palette
- Background: `#FFFFFF`
- Primary Text: `#111827`
- Secondary Text: `#4B5563`
- Divider / Border: `#E5E7EB`
- Soft Accent 1: `#DCEEFE`
- Soft Accent 2: `#DDF6F1`
- Soft Accent 3: `#F3F7FB`
- Strong Accent: `#2F6FED` or `#138A72`

### Gradient Principles
- Do not fill the entire background with gradients.
- Use gradients only as localized decorative elements.
- Recommended uses:
- top or side glow on the title slide
- background for section dividers
- a small halo behind a figure
- accent lines or underline bars

### Recommended Gradient Examples
```css
linear-gradient(135deg, rgba(47,111,237,0.10), rgba(19,138,114,0.08))
```

```css
radial-gradient(circle at top right, rgba(47,111,237,0.10), transparent 45%)
```

```css
linear-gradient(180deg, rgba(221,246,241,0.55), rgba(255,255,255,0))
```

### Prohibited Choices
- No overly saturated neon colors
- No purple-led default theme
- No switch to dark backgrounds
- No overuse of large color-filled boxes behind body text

## 5. Slide Types

### 5.1 Title Slide
- The first page should be a dedicated title slide
- Include:
- paper title
- subtitle or one-line description
- presenter: use the name and role listed in the slide content markdown (e.g., `Elmo Shim` for the current project)
- conference or review session information may be placed in small text at the bottom if needed
- A figure is optional. If included, use only a very restrained hero image

### 5.2 Section Divider
- May be used before `Introduction`, `Methods`, `Experiments`, and `Conclusion`
- Place only a large title and small subtext
- Do not include body bullets
- A soft gradient block or thin accent bar is allowed

### 5.3 Text + Figure Slide
- This is the default format
- Use a `45:55` or `40:60` ratio
- If the text becomes long, keep only one figure; if the figure is complex, reduce the text even further
- Show the figure reference near the bottom of the slide or near the figure caption

### 5.4 Figure-first Slide
- Suitable for experiment results, ablations, and qualitative results
- Make the figure the main subject of the slide
- Limit text to one takeaway line at the top and 2-3 bullets at the bottom

### 5.5 Comparison Slide
- Use for baseline comparisons or ablations
- Keep column alignment strict
- Strong color emphasis should be used only for `Ours`
- Keep everything else in a neutral tone

### 5.6 Conclusion Slide
- One takeaway sentence
- No more than 3 supporting bullets
- If possible, reuse a figure such as Figure 2 or Figure 10 to bring back the core idea of the paper

## 6. Figure Usage Rules

### Core Principles
- Do not crop or distort figures in a way that changes their original meaning.
- Summarize caption text separately on the slide rather than repeating the full original caption verbatim.
- If multiple figures appear on one slide, make the viewing order visually clear.

### Placement Rules
- Secure enough whitespace around each figure
- Allow only a thin border or a very soft shadow
- If the paper figure already has a white background, place it naturally rather than forcing it into a floating card
- Recommended figure number format:
- `Figure 10. Divide-and-conquer inference`

### Emphasis Rules
- If emphasis is needed, prefer these methods over solid color boxes:
- thin outline
- semi-transparent highlight
- short callout label
- Use arrows sparingly

## 7. Text Rules for Research Presentation

### Sentence Style
- Prefer `assertive summary` over explanatory prose
- Example:
- Bad: "This method seems to perform well in several aspects."
- Good: "Mesh-native decoding substantially reduces boundary jaggedness."

### Bullet Writing Guidelines
- A bullet does not need to be a complete sentence
- But avoid vague fragmentary notes with no subject or claim
- Each bullet should contain only one assertion

### Emphasis Priority
- First: weight
- Second: position
- Third: color
- Avoid relying on color alone for emphasis

## 8. Motion and Transition

### Principle
- Keep animation minimal
- Use motion only when it helps the order of information reveal

### Allowed Motion
- fade in
- slight upward reveal
- soft background transition on section divider slides

### Disallowed Motion
- bounce
- excessive zoom usage
- rotation or heavy parallax
- interactions where elements repeatedly jump around within a single slide

## 9. Presentation Controls

### Fullscreen Mode
- Presentation HTML should support a `Fullscreen` toggle by default.
- It should use the browser Fullscreen API.
- Place a `Fullscreen` button in the bottom-right navigation area.
- The shortcut key `F` should toggle fullscreen mode.
- In fullscreen mode, it is recommended that the button label change to `Exit Fullscreen`.

### Navigation Shortcuts
- Next slide: `ArrowRight`, `PageDown`, `Space`
- Previous slide: `ArrowLeft`, `PageUp`
- First slide: `Home`
- Last slide: `End`
- Toggle fullscreen: `F`

### Control Hint
- Keep a short control hint near the bottom of the screen.
- Recommended example:
- `Arrow keys / Space / Home / End / F`
- The hint should be small and light enough that it does not interfere with the presentation flow

### Interaction with Zoom Popups
- Clicking a figure may open a zoom popup.
- While a popup is open, slide navigation shortcuts must be disabled.
- The popup should close with `Esc` or a background click

## 10. HTML/CSS Implementation Rules

### Structural Principles
- Each slide should be an independent `section` or `article`
- Manage shared styles with CSS variables
- Do not hardcode colors, spacing, radius, or shadow values; define them as tokens

### Recommended CSS Variables
```css
:root {
  --bg: #ffffff;
  --text: #111827;
  --muted: #4b5563;
  --line: #e5e7eb;
  --accent-blue: #2f6fed;
  --accent-green: #138a72;
  --accent-soft-blue: #dceefe;
  --accent-soft-green: #ddf6f1;
  --accent-soft-gray: #f3f7fb;
  --shadow-soft: 0 10px 30px rgba(17, 24, 39, 0.06);
  --radius-lg: 24px;
  --radius-md: 16px;
}
```

### Minimum Component Set
- `.slide`
- `.slide-title`
- `.slide-kicker`
- `.slide-body`
- `.figure-panel`
- `.figure-caption`
- `.key-message`
- `.ref-note`

### Implementation Rules
- Fix every slide height to the viewport
- Do not allow vertical scrolling, even if content grows
- If content overflows, split the layout differently or add another slide
- Preserve image aspect ratios; never force stretching

### Interaction Components
- Default navigation buttons:
- `Prev`
- `Next`
- `Fullscreen`
- A progress bar may be placed at the bottom of the slide to show progress
- The modal overlay for figure zoom should sit on a layer above the main content

## 11. Recommended Visual Motifs

### Acceptable Design Accents
- a very soft radial gradient in the top corner
- a short gradient line under the title
- a large blurred circular background on section transition slides
- a small accent block next to a key sentence

### Design Motifs to Avoid
- repeating background patterns
- excessive glassmorphism
- shapes that draw more attention than the main content
- a different visual language on every slide

## 12. Content Mapping from Current Markdown

Current draft document:
- [SATO_review_slides.md](SATO_review_slides.md)

Apply the following principles during HTML conversion:

- The first slide must be a dedicated title page
- Content should begin from the following slide
- In the `Experiments` section, increase the share of figure-first slides
- In the `Methods` section, use diagram-centered composition so the sequence flow is visible
- In the `Conclusion` section, reduce text volume and focus on takeaways

### Iteration Workflow
- The output HTML file lives next to the slide content markdown (e.g., `SATO_review_slides.html`).
- Edits happen on the HTML directly while the user views it in a browser — reopen/refresh to see changes.
- For local file viewing, opening the HTML via the file system is sufficient; images use relative paths and load without a server.

## 13. Final Quality Checklist

Check the following items before and after producing the HTML slides.

- Is the first page separated as a standalone title slide?
- Is the presenter name and role rendered correctly (matching the value in the slide content markdown)?
- Is the overall background kept white-based throughout?
- Are gradients limited to decorative accents?
- Does each slide read as having one core message?
- Does the text avoid feeling too dense?
- Are the figures shown large enough?
- Is the visual emphasis on `Ours` consistent?
- Are footer, reference, and caption styles consistent?
- Does the explanation flow feel natural at presentation pace?
- Do the fullscreen button and `F` shortcut work?
- Does the figure zoom popup work, and does it close with `Esc`?
