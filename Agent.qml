import QtQuick
import Quickshell.Io

// One agent's usage record, read straight off the data file in
// ~/.local/state/omarchy/agents/usage/. Packaged collectors write claude /
// codex / fireworks; collect-grok.py writes grok.json. The panel never learns
// how the numbers were made — a record in that directory is an agent.
Item {
  id: root
  visible: false

  property string agentId: ""
  property string path: ""
  property var record: null

  FileView {
    path: root.path
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.parse(text())
    onLoadFailed: root.record = null
  }

  function parse(content) {
    try {
      var parsed = JSON.parse(String(content || ""))
      root.record = parsed && typeof parsed === "object" ? parsed : null
    } catch (e) {
      console.warn("agents", "Ignoring bad usage record", root.path, e)
      root.record = null
    }
  }
}
