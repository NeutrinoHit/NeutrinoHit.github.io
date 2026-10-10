.PHONY: site local-aggregate book-covers check-book-covers book-covers-full export-book-covers sync-book-covers check-book-cover-sync

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

book-covers:
	python assets/books/covers/source/generate_series.py
	python assets/books/covers/source/generate_statistical_v2.py
	python assets/books/covers/source/generate_neutrino_v2.py
	python assets/books/covers/source/generate_neutrino_back_proposal.py

check-book-covers: book-covers
	python assets/books/covers/source/validate_series.py

export-book-covers: check-book-covers
	python assets/books/covers/source/export_book_covers.py

sync-book-covers:
	python assets/books/covers/source/export_book_covers.py --sync

check-book-cover-sync:
	python assets/books/covers/source/export_book_covers.py --check-sync

book-covers-full:
	python assets/books/covers/source/physics/generate_juno_model.py
	python assets/books/covers/source/artwork/generate_statistical_methods_artwork.py
	python assets/books/covers/source/brand/generate_logo.py
	python assets/books/covers/source/generate_series.py
	python assets/books/covers/source/generate_statistical_v2.py
	python assets/books/covers/source/generate_neutrino_v2.py
	python assets/books/covers/source/generate_neutrino_back_proposal.py
	python assets/books/covers/source/validate_series.py
