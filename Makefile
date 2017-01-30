.PHONY: scrape
scape:
	python3 colloq.py > colloq.ics

.PHONY: deploy
DEST := courses:coursewww/capra.cs.cornell.edu/htdocs
deploy: scrape
	scp colloq.ics $(DEST)
