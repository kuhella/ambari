SET search_path=ambari;
IF EXISTS (SELECT * FROM pg_table WHERE tablename=repo_version) THEN
    UPDATE cluster_version SET state='CURRENT' where repo_version_id=(SELECT repo_version_id FROM repo_version;
END IF;
