TARGET_DIR := targets/
STAGING_DIR := staging/

GET_TARGET = $(firstword $(subst _, ,$1))
clean:
	@rm -rf $(STAGING_DIR)

bae_checkout:
	svn co `cat $(TARGET_DIR)/$(call GET_TARGET,$@)/SVN_URL` $(STAGING_DIR)

bae_files:
	@rsync -av \
		--exclude='.git' \
		--exclude='$(TARGET_DIR)'  \
		--exclude='$(STAGING_DIR)' \
		--exclude='Makefile'  \
		--exclude='sqlite.db' \
		--exclude='SVN_URL' \
		--exclude='*.pyc' \
		--exclude='manage.py' \
		--exclude='*.example.py' \
		./* $(STAGING_DIR)/
	cp -r $(TARGET_DIR)/$(call GET_TARGET,$@)/* $(STAGING_DIR)/
	
bae_commit:
	cd $(STAGING_DIR) && svn add --force .
	cd $(STAGING_DIR) && svn commit -m "Automatic deployment."
	
bae: clean bae_files

bae_deploy: clean bae_checkout bae_files bae_commit

.PHONY: bae 