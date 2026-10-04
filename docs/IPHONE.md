# iPhone companion: documented Shortcut

Status: recipe based on Apple documentation; **untested on an actual iPhone and not simulator-tested** in this workspace. Exact-dot opening is not established. No native iOS binary, login or store enrollment is required.

## Start with Open ChatGPT

1. Install/update the official ChatGPT app on a supported iPhone. Sign into the account/workspace that has your dot. Create the dot on desktop first if required by OpenAI's current rollout.
2. Open Apple Shortcuts, create a new shortcut and add the **Open App** action. Select the installed **ChatGPT** app using Apple's app picker, not a guessed URL scheme.
3. Name it **Open ChatGPT**. Run it from Shortcuts and confirm ChatGPT opens. Inside the app, select your existing dot. That remaining step must be explicit.
4. Use shortcut Details → **Add to Home Screen**. Choose your own icon or the project's original seed PNG if you want, and keep the label Open ChatGPT.
5. For a widget, add a **Shortcuts** widget to the Home Screen. Edit the widget to select this shortcut or the folder containing it. Tap it and verify the same launch behavior. An action may open Shortcuts on its way to the target app.

Apple documents [Home Screen shortcuts](https://support.apple.com/guide/shortcuts/apd735880972/ios) and [Shortcuts widgets](https://support.apple.com/guide/shortcuts/apd029b36d05/ios). Menu wording can vary with the installed iOS version.

## Conditional exact-link option

Only attempt this with a private HTTPS link you obtained from your own dot, and only if the current OpenAI integration documentation authorizes that surface. Do not generate or share a public ChatGPT conversation link.

Create a separate test Shortcut with **URL** (your private HTTPS URL) → **Open URLs**. Test on the physical iPhone with the installed supported ChatGPT app, both cold and warm. Check that it opens the **correct existing dot inside the app**, under the right account/workspace. Confirm signed-out and offline outcomes honestly. This recipe is not a claim of a documented OpenAI exact-dot app link.

If it routes to Safari, an ordinary chat, login or an unsupported page, keep the Open App recipe and label **Open ChatGPT**. Mobile web is explicitly unsupported for dots; Safari is not a working dot fallback. Save the private test link only on that phone and do not publish it with test evidence.

Only after a successful actual-device test may the URL shortcut be labelled **Open my dot** for that particular device. Retest after relevant ChatGPT/iOS updates; there is no established stable third-party routing contract in the sources checked here. [OpenAI supported messaging surfaces](https://learn.chatgpt.com/docs/dots/channels)

## Native iOS is a later decision

A SwiftUI/WidgetKit app may make setup more convenient, but widget links first open the containing app and its onward handoff needs validation. iOS does not provide an arbitrary floating companion above other apps or continuously animated Home Screen widgets for this use. Do not invent background dot activity.

Native builds require Apple developer-account access, signing/provisioning and an approved distribution plan; App Store submission adds review. A thin launcher can face minimum-functionality review under 4.2. Confirm costs and submission scope before enrollment. Native binary updates follow Apple distribution and user settings, not Tauri's desktop updater. [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
