.PHONY: site local-aggregate

site:
	rm -rf _site
	NEUTRINOHIT_SYNC_PROJECT_SITES=0 quarto render
	rm -rf _site/neutrino_introduction
	rm -f \
		_site/albums/10-17-may-2026/photos/03-image-20260515123220-426-177.jpg \
		_site/albums/10-17-may-2026/photos/04-img-5737.jpeg \
		_site/albums/10-17-may-2026/photos/05-img-5729.jpeg \
		_site/albums/10-17-may-2026/photos/06-img-5726.jpeg \
		_site/albums/10-17-may-2026/photos/07-img-5712.jpeg \
		_site/albums/10-17-may-2026/photos/08-img-5687.jpeg \
		_site/albums/10-17-may-2026/photos/08-img-5737.jpeg \
		_site/albums/10-17-may-2026/photos/09-img-5684.jpeg \
		_site/albums/10-17-may-2026/photos/10-img-5707.jpeg

local-aggregate: site
	NEUTRINOHIT_SYNC_PROJECT_SITES=1 python scripts/sync_local_project_sites.py
