import { call } from "./platform";
import type { Avatar } from "./types";

// All file selection and image processing stays in Rust. This dialog only
// chooses the import mode; it never reads files, account tokens or remote art.
export function bindAppearance(
  button: HTMLElement,
  apply: (value: Avatar) => void,
) {
  const dialog = document.createElement("dialog");
  dialog.className = "appearance-dialog";
  dialog.setAttribute("aria-labelledby", "appearance-title");
  dialog.innerHTML = `<h2 id="appearance-title">Your companion</h2>
    <p>Use your existing pet or choose a different icon.</p>
    <div class="appearance-options">
      <button type="button" data-kind="pet">Import pet sprite sheet</button>
      <p>Download your pet from ChatGPT’s pet settings, then choose its PNG sheet. We extract the original first idle frame.</p>
      <button type="button" data-kind="image" class="secondary">Choose local image</button>
      <p>Any still PNG up to 1024 × 1024 and 4 MiB.</p>
      <button type="button" data-kind="default" class="text-button">Restore default image</button>
    </div>
    <p>Images stay on this device. This does not sync with ChatGPT.</p>
    <p class="appearance-status" role="status"></p>
    <button type="button" class="secondary" data-close>Done</button>`;
  document.body.append(dialog);
  const status = dialog.querySelector<HTMLElement>(".appearance-status")!;
  const choices = [
    ...dialog.querySelectorAll<HTMLButtonElement>("[data-kind]"),
  ];
  for (const choice of choices) {
    choice.onclick = async () => {
      choices.forEach((item) => (item.disabled = true));
      status.textContent = "Choose a file in the system picker…";
      try {
        const kind = choice.dataset.kind;
        apply(
          await call<Avatar>(
            kind === "default" ? "reset_avatar" : "import_avatar",
            kind === "default" ? undefined : { kind },
          ),
        );
        status.textContent =
          "Your current image is shown on the companion. Previous images are preserved locally.";
      } catch (error) {
        status.textContent =
          typeof error === "string"
            ? error
            : error instanceof Error
              ? error.message
              : "Image could not be imported.";
      } finally {
        choices.forEach((item) => (item.disabled = false));
      }
    };
  }
  dialog.querySelector<HTMLButtonElement>("[data-close]")!.onclick = () =>
    dialog.close();
  button.onclick = () => {
    status.textContent = "";
    dialog.showModal();
  };
}
