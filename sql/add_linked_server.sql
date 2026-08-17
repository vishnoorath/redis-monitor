EXEC sp_addlinkedserver
    @server     = N'10.10.98.26',
    @srvproduct = N'',
    @provider   = N'SQLNCLI',
    @datasrc     = N'10.10.98.26,31813',   -- port here
    @catalog    = N'NitaraDB';
EXEC sp_addlinkedsrvlogin
    @rmtsrvname = N'10.10.98.26',
    @useself    = N'True';                  -- pass-through the current login