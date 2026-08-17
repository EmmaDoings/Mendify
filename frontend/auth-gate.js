(function () {
  try {
    // Hide protected UI until auth is verified.
    // NOTE: visibility:hidden is sufficient to prevent FOUC.
    //       overflow:hidden was previously also set here but caused a bug where
    //       the document remained un-scrollable because init() only ever reset
    //       visibility, never overflow. Removed.
    window.__MENDIFY_AUTH_GATE__ = true;

    document.documentElement.style.visibility = 'hidden';

    const token = window.localStorage.getItem('access_token');
    if (!token) {
      // Ensure we don't stay hidden on redirect / failed navigation.
      document.documentElement.style.visibility = 'visible';
      window.location.replace('login.html');
      return;
    }

    // Safety timeout: if init() never runs or hangs (e.g. backend offline),
    // make the page visible so the user isn't stuck on a blank screen.
    setTimeout(function () {
      if (document.documentElement.style.visibility === 'hidden') {
        document.documentElement.style.visibility = 'visible';
      }
    }, 8000);

  } catch (e) {
    // If storage / CSP blocks access, fail open to avoid a blank page.
    window.__MENDIFY_AUTH_GATE__ = false;
    document.documentElement.style.visibility = 'visible';
  }
})();