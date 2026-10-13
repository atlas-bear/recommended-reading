// Draws a repository block in the navbar (name, latest release, stars, forks),
// the way Material for MkDocs does. Reads the public GitHub API once a day per
// browser and keeps the result in localStorage; falls back to the name alone.
(function () {
  var owner = "atlas-bear";
  var repo = "recommended-reading";
  var key = "atlas-repo-stats:" + owner + "/" + repo;
  var ttl = 24 * 60 * 60 * 1000;

  function icon() {
    return '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>';
  }

  function render(stats) {
    var nav = document.querySelector("#navbarCollapse .navbar-nav.ms-auto, #navbarCollapse .navbar-nav:last-of-type");
    if (!nav || document.querySelector(".atlas-repo")) return;
    var li = document.createElement("li");
    li.className = "nav-item";
    var facts = [];
    if (stats.release) facts.push("<span>" + stats.release + "</span>");
    if (typeof stats.stars === "number") facts.push("<span>" + stats.stars + " stars</span>");
    if (typeof stats.forks === "number") facts.push("<span>" + stats.forks + " forks</span>");
    li.innerHTML =
      '<a class="atlas-repo" href="https://github.com/' + owner + "/" + repo + '" title="Repository on GitHub">' +
      icon() +
      '<span><span class="atlas-repo__name">' + owner + "/" + repo + "</span>" +
      (facts.length ? '<br><span class="atlas-repo__facts">' + facts.join("") + "</span>" : "") +
      "</span></a>";
    var github = nav.querySelector('a[href="https://github.com/' + owner + "/" + repo + '"]');
    if (github && github.closest("li")) github.closest("li").remove();
    nav.appendChild(li);
  }

  function load() {
    try {
      var cached = JSON.parse(localStorage.getItem(key) || "null");
      if (cached && Date.now() - cached.at < ttl) return render(cached);
    } catch (e) {}
    var stats = { at: Date.now() };
    fetch("https://api.github.com/repos/" + owner + "/" + repo)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (d) { stats.stars = d.stargazers_count; stats.forks = d.forks_count; }
        return fetch("https://api.github.com/repos/" + owner + "/" + repo + "/releases/latest");
      })
      .then(function (r) { return r && r.ok ? r.json() : null; })
      .then(function (d) {
        if (d && d.tag_name) stats.release = d.tag_name;
        try { localStorage.setItem(key, JSON.stringify(stats)); } catch (e) {}
        render(stats);
      })
      .catch(function () { render(stats); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
