// Client-side plugin: registers @iframe-resizer/child so the DPSA portal
// (which embeds this app in an <iframe>) can auto-size the frame to the
// chat widget's content height. Must run only in the browser.
import '@iframe-resizer/child'

export default defineNuxtPlugin(() => {
  // Side-effect import above is enough — the child script attaches itself
  // to window and starts posting size messages to the parent frame.
})
