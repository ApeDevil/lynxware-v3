// The only script on the site. It replaces the Wix runtime features the pages use:
// the mobile menu and the video players (consent before anything loads from YouTube).
(() => {
	// Mobile menu: Wix toggles these exact classes; the captured CSS already styles both states.
	const menu = document.getElementById('MENU_AS_CONTAINER');
	const toggle = document.getElementById('MENU_AS_CONTAINER_TOGGLE');
	if (menu && toggle) {
		const set = (open) => {
			menu.classList.toggle('I_VSKP', open);
			menu.dataset.undisplayed = String(!open);
			toggle.classList.toggle('d0L2ow', open);
			toggle.setAttribute('aria-label', open ? 'Close navigation menu' : 'Open navigation menu');
			toggle.setAttribute('aria-expanded', String(open));
			document.body.classList.toggle('siteScrollingBlockedIOSFix', open);
		};
		const flip = () => set(menu.dataset.undisplayed !== 'false');
		toggle.addEventListener('click', flip);
		toggle.addEventListener('keydown', (e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				flip();
			}
		});
		document.addEventListener('keydown', (e) => e.key === 'Escape' && set(false));
		menu.addEventListener('click', (e) => {
			if (e.target === menu || e.target.closest('a')) set(false);
		});
	}

	// Desktop "More" dropdown in the header (Wix opens it on hover with JS).
	for (const more of document.querySelectorAll('[data-testid="linkElement"][aria-haspopup="true"], li[data-testid="lineMenuMoreButton"]')) {
		const li = more.closest('li') || more;
		li.addEventListener('mouseenter', () => li.setAttribute('data-hovered', 'true'));
		li.addEventListener('mouseleave', () => li.removeAttribute('data-hovered'));
	}

	// Videos: nothing is requested from YouTube until the visitor clicks play.
	for (const box of document.querySelectorAll('.lx-video')) {
		box.querySelector('.lx-video__play').addEventListener('click', () => {
			const f = document.createElement('iframe');
			f.src = `https://www.youtube-nocookie.com/embed/${box.dataset.youtube}?autoplay=1&rel=0`;
			f.title = 'YouTube video';
			f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
			f.allowFullscreen = true;
			box.replaceChildren(f);
		});
	}
})();

// Mobile "back to top" button: Wix shows it once the page is scrolled.
(() => {
	const btn = document.getElementById('BACK_TO_TOP_BUTTON');
	if (!btn) return;
	btn.setAttribute('role', 'button');
	btn.setAttribute('aria-label', 'Back to top');
	btn.tabIndex = 0;
	const update = () => {
		const show = window.scrollY > window.innerHeight / 2;
		btn.style.opacity = show ? '1' : '';
		btn.style.visibility = show ? 'visible' : '';
		btn.style.transition = show ? 'opacity .5s' : '';
	};
	addEventListener('scroll', update, { passive: true });
	const top = () => scrollTo({ top: 0, behavior: 'smooth' });
	btn.addEventListener('click', top);
	btn.addEventListener('keydown', (e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), top()));
})();
