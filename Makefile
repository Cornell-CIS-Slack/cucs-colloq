.PHONY: colloq.ics
colloq.ics:
	python3 colloq.py > $@

.PHONY: deploy
DEST := courses:coursewww/capra.cs.cornell.edu/htdocs
deploy: colloq.ics
	scp $^ $(DEST)
