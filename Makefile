TARGET_DIR := targets/
STAGING_DIR := staging/

GET_TARGET = $(firstword $(subst _, ,$1))
clean:
	@rm -rf $(STAGING_DIR)

bae_checkout:
	@echo Initialising SVN repository...
	@svn co `cat $(TARGET_DIR)/$(call GET_TARGET,$@)/SVN_URL` $(STAGING_DIR)/tmp >/dev/null
	@mv $(STAGING_DIR)/tmp/.svn $(STAGING_DIR)/
	@rm -rf $(STAGING_DIR)/tmp

bae_files:
	@echo Collecting project files...
	@mkdir -p $(STAGING_DIR)/static >/dev/null
	@python manage.py collectstatic -c --noinput >/dev/null
	@rsync -av \
		--exclude='.*' \
		--exclude='static' \
		--exclude='$(TARGET_DIR)'  \
		--exclude='$(STAGING_DIR)' \
		--exclude='Makefile'  \
		--exclude='sqlite.db' \
		--exclude='*.pyc' \
		--exclude='*.bak' \
		--exclude='*.example.py' \
		./ $(STAGING_DIR)/ >/dev/null
	@cp -r $(TARGET_DIR)/$(call GET_TARGET,$@)/* $(STAGING_DIR)/
	@rm $(STAGING_DIR)/manage.py
	@rm $(STAGING_DIR)/SVN_URL
bae_commit:
	@echo Committing to Remote...
	@cd $(STAGING_DIR) && svn add --force .
	@cd $(STAGING_DIR) && svn status | sed -e '/^!/!d' -e 's/^!//' | xargs -r svn rm
	@cd $(STAGING_DIR) && svn commit -m "Automatic deployment."
	
bae: clean bae_files

bae_deploy: clean bae_checkout bae_files bae_commit

.PHONY: bae 