import Link from "next/link";

const footerLinks = {
  about: [
    { name: "About Civitas", href: "/" },
    { name: "GitHub", href: "https://github.com/baytides/civitas", external: true },
  ],
  track: [
    { name: "Project 2025 Tracker", href: "/tracker" },
    { name: "State Map", href: "/states" },
    { name: "Timeline", href: "/timeline" },
  ],
  action: [
    { name: "Take Action", href: "/resistance" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t bg-muted/50">
      <div className="container py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <Link href="/" className="text-2xl font-bold text-primary">
              Civitas
            </Link>
            <p className="text-sm text-muted-foreground">
              Tracking Project 2025 implementation to protect American democracy.
            </p>
            <p className="text-xs text-muted-foreground">
              Data updated daily from official government sources.
            </p>
          </div>

          {/* About */}
          <div>
            <h3 className="font-semibold mb-4">About</h3>
            <ul className="space-y-2">
              {footerLinks.about.map((link) => (
                <li key={link.name}>
                  {"external" in link && link.external ? (
                    <a
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Track */}
          <div>
            <h3 className="font-semibold mb-4">Track</h3>
            <ul className="space-y-2">
              {footerLinks.track.map((link) => (
                <li key={link.name}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Action */}
          <div>
            <h3 className="font-semibold mb-4">Take Action</h3>
            <ul className="space-y-2">
              {footerLinks.action.map((link) => (
                <li key={link.name}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Project Civitas. Open source and
            available under MIT license.
          </p>
          <div className="flex items-center space-x-4">
            <a
              href="https://github.com/baytides/civitas"
              className="text-xs text-muted-foreground hover:text-foreground"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
