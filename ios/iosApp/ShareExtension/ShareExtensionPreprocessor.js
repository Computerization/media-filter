class ShareExtensionPreprocessor {
  run({ completionFunction }) {
    // Try to get the FULL original URL (WeChat pages modify URL via history.replaceState)
    var fullURL = null;

    // Priority 1: Check og:url meta tag (often has the original full URL)
    var ogUrl = document.querySelector('meta[property="og:url"]');
    if (ogUrl && ogUrl.content) {
      fullURL = ogUrl.content;
    }

    // Priority 2: Check canonical link
    if (!fullURL) {
      var canonical = document.querySelector('link[rel="canonical"]');
      if (canonical && canonical.href) {
        fullURL = canonical.href;
      }
    }

    // Priority 3: Check twitter:url meta tag
    if (!fullURL) {
      var twitterUrl = document.querySelector('meta[name="twitter:url"]');
      if (twitterUrl && twitterUrl.content) {
        fullURL = twitterUrl.content;
      }
    }

    // Priority 4: Fall back to window.location.href
    if (!fullURL) {
      fullURL = window.location.href;
    }

    // Priority 5: Last resort - document.baseURI
    if (!fullURL) {
      fullURL = document.baseURI;
    }

    completionFunction({
      baseURI: fullURL,
      title: document.title,
    });
  }
}
var ExtensionPreprocessingJS = new ShareExtensionPreprocessor();
