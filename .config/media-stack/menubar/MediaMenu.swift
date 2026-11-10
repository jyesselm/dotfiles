// Menu-bar icon for the media stack: click → the dashboard; the menu lists the other pages.
// Build and install with ./install.sh (compiles into ~/Applications/Media Menu.app and loads the launchd agent).
import AppKit

let pages: [(String, String)] = [
    ("Dashboard", "http://localhost:3000"),
    ("Plex", "http://localhost:32400/web"),
    ("Seerr (requests)", "http://localhost:5055"),
    ("Audiobookshelf", "http://localhost:13378"),
    ("Media Index", "http://localhost:8686"),
    ("qBittorrent", "http://localhost:8080"),
]

final class App: NSObject, NSApplicationDelegate {
    var item: NSStatusItem!

    func applicationDidFinishLaunching(_ note: Notification) {
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let icon = NSImage(systemSymbolName: "play.tv", accessibilityDescription: "Media")
        icon?.isTemplate = true
        item.button?.image = icon
        item.button?.toolTip = "Media stack — click for the dashboard, right-click for more"
        item.button?.target = self
        item.button?.action = #selector(click)
        item.button?.sendAction(on: [.leftMouseUp, .rightMouseUp])
    }

    @objc func click() {
        if NSApp.currentEvent?.type == .rightMouseUp {
            let menu = NSMenu()
            for (i, p) in pages.enumerated() {
                let m = NSMenuItem(title: p.0, action: #selector(open(_:)), keyEquivalent: i == 0 ? "d" : "")
                m.representedObject = p.1
                m.target = self
                menu.addItem(m)
            }
            menu.addItem(.separator())
            menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
            item.menu = menu
            item.button?.performClick(nil)
            item.menu = nil
        } else {
            NSWorkspace.shared.open(URL(string: pages[0].1)!)
        }
    }

    @objc func open(_ sender: NSMenuItem) {
        if let s = sender.representedObject as? String, let u = URL(string: s) { NSWorkspace.shared.open(u) }
    }
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.accessory)  // no Dock icon
app.run()
