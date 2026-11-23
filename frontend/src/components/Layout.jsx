
import React, { useLayoutEffect, useRef } from 'react';
import { Outlet, useLocation, useNavigationType } from 'react-router-dom';

import Navbar from './Navbar.jsx';
import Footer from './Footer.jsx';

export default function Layout() {
  const { pathname, hash } = useLocation();
  const navigationType = useNavigationType();
  const main = useRef(null);

  useLayoutEffect(() => {
    if (hash) {
      const target = document.getElementById(hash.slice(1));
      target?.scrollIntoView();
      target?.focus({ preventScroll: true });
    } else if (navigationType !== 'POP') {
      window.scrollTo(0, 0);
      main.current?.focus({ preventScroll: true });
    }
  }, [pathname, hash, navigationType]);

  return (
    <>
      <Navbar />

      <main ref={main} tabIndex={-1}>
        <Outlet />
      </main>

      <Footer />
    </>
  );
}
