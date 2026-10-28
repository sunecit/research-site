// Render the delimiters produced by pymdownx.arithmatex.
// Libraries and fonts are served locally with the site.
document$.subscribe(({ body }) => {
  const content = body.querySelector(".md-content");
  if (!content) return;
  renderMathInElement(content, {
    delimiters: [
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false }
    ],
    throwOnError: true,
    trust: false
  });
});
