######################################################################
#
# SETUP
#
#______________________________________________________________________
#
# STEP 0: DOWNLOADS
#______________________________________________________________________
#

# dir: intertwine/platform
cd data/geos
mkdir tmp
cd tmp

# Download 2010 US Census National Places Gazetteer Files (1.2MB)
# dir: intertwine/platform/data/geos/tmp
curl "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/Gaz_places_national.zip" -o "Gaz_places_national.zip"
unzip Gaz_places_national.zip

# Download 2010 US Census Urban Rural Update 1 National File (1.45GB - this can take a while)
# dir: intertwine/platform/data/geos/tmp
curl "https://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National/us2010.ur1.zip" -o "us2010.ur1.zip"
unzip us2010.ur1.zip -d us2010.ur1

# If following steps sequentially (strongly recommended):
cd ..

#______________________________________________________________________
#
# STEP 1: PRE-PROCESS GEOGRAPHIC HEADER RECORD (GHR) FILE
#______________________________________________________________________
#

# Load Geographic Header Record (GHR)
# dir: intertwine/platform/data/geos
sqlite3 geo.db
CREATE TABLE ghr_bulk (full_string CHAR);
.import tmp/us2010.ur1/usgeo2010.ur1 ghr_bulk

# Split fixed-width GHR into separate columns (all text)
# sqlite3 geo.db
CREATE TABLE ghr_txt AS
SELECT
    trim(SUBSTR(full_string,1,6)) AS FILEID,
    trim(SUBSTR(full_string,7,2)) AS STUSAB,
    trim(SUBSTR(full_string,9,3)) AS SUMLEV,
    trim(SUBSTR(full_string,12,2)) AS GEOCOMP,
    trim(SUBSTR(full_string,14,3)) AS CHARITER,
    trim(SUBSTR(full_string,17,2)) AS CIFSN,
    trim(SUBSTR(full_string,19,7)) AS LOGRECNO,
    trim(SUBSTR(full_string,26,1)) AS REGION,
    trim(SUBSTR(full_string,27,1)) AS DIVISION,
    trim(SUBSTR(full_string,28,2)) AS STATE,
    trim(SUBSTR(full_string,30,3)) AS COUNTY,
    trim(SUBSTR(full_string,33,2)) AS COUNTYCC,
    trim(SUBSTR(full_string,35,2)) AS COUNTYSC,
    trim(SUBSTR(full_string,37,5)) AS COUSUB,
    trim(SUBSTR(full_string,42,2)) AS COUSUBCC,
    trim(SUBSTR(full_string,44,2)) AS COUSUBSC,
    trim(SUBSTR(full_string,46,5)) AS PLACE,
    trim(SUBSTR(full_string,51,2)) AS PLACECC,
    trim(SUBSTR(full_string,53,2)) AS PLACESC,
    trim(SUBSTR(full_string,55,6)) AS TRACT,
    trim(SUBSTR(full_string,61,1)) AS BLKGRP,
    trim(SUBSTR(full_string,62,4)) AS BLOCK,
    trim(SUBSTR(full_string,66,2)) AS IUC,
    trim(SUBSTR(full_string,68,5)) AS CONCIT,
    trim(SUBSTR(full_string,73,2)) AS CONCITCC,
    trim(SUBSTR(full_string,75,2)) AS CONCITSC,
    trim(SUBSTR(full_string,77,4)) AS AIANHH,
    trim(SUBSTR(full_string,81,5)) AS AIANHHFP,
    trim(SUBSTR(full_string,86,2)) AS AIANHHCC,
    trim(SUBSTR(full_string,88,1)) AS AIHHTLI,
    trim(SUBSTR(full_string,89,3)) AS AITSCE,
    trim(SUBSTR(full_string,92,5)) AS AITS,
    trim(SUBSTR(full_string,97,2)) AS AITSCC,
    trim(SUBSTR(full_string,99,6)) AS TTRACT,
    trim(SUBSTR(full_string,105,1)) AS TBLKGRP,
    trim(SUBSTR(full_string,106,5)) AS ANRC,
    trim(SUBSTR(full_string,111,2)) AS ANRCCC,
    trim(SUBSTR(full_string,113,5)) AS CBSA,
    trim(SUBSTR(full_string,118,2)) AS CBSASC,
    trim(SUBSTR(full_string,120,5)) AS METDIV,
    trim(SUBSTR(full_string,125,3)) AS CSA,
    trim(SUBSTR(full_string,128,5)) AS NECTA,
    trim(SUBSTR(full_string,133,2)) AS NECTASC,
    trim(SUBSTR(full_string,135,5)) AS NECTADIV,
    trim(SUBSTR(full_string,140,3)) AS CNECTA,
    trim(SUBSTR(full_string,143,1)) AS CBSAPCI,
    trim(SUBSTR(full_string,144,1)) AS NECTAPCI,
    trim(SUBSTR(full_string,145,5)) AS UA,
    trim(SUBSTR(full_string,150,2)) AS UASC,
    trim(SUBSTR(full_string,152,1)) AS UATYPE,
    trim(SUBSTR(full_string,153,1)) AS UR,
    trim(SUBSTR(full_string,154,2)) AS CD,
    trim(SUBSTR(full_string,156,3)) AS SLDU,
    trim(SUBSTR(full_string,159,3)) AS SLDL,
    trim(SUBSTR(full_string,162,6)) AS VTD,
    trim(SUBSTR(full_string,168,1)) AS VTDI,
    trim(SUBSTR(full_string,169,3)) AS RESERVE2,
    trim(SUBSTR(full_string,172,5)) AS ZCTA5,
    trim(SUBSTR(full_string,177,5)) AS SUBMCD,
    trim(SUBSTR(full_string,182,2)) AS SUBMCDCC,
    trim(SUBSTR(full_string,184,5)) AS SDELM,
    trim(SUBSTR(full_string,189,5)) AS SDSEC,
    trim(SUBSTR(full_string,194,5)) AS SDUNI,
    trim(SUBSTR(full_string,199,14)) AS AREALAND,
    trim(SUBSTR(full_string,213,14)) AS AREAWATR,
    trim(SUBSTR(full_string,227,90)) AS NAME,
    trim(SUBSTR(full_string,317,1)) AS FUNCSTAT,
    trim(SUBSTR(full_string,318,1)) AS GCUNI,
    trim(SUBSTR(full_string,319,9)) AS POP100,
    trim(SUBSTR(full_string,328,9)) AS HU100,
    trim(SUBSTR(full_string,337,11)) AS INTPTLAT,
    trim(SUBSTR(full_string,348,12)) AS INTPTLON,
    trim(SUBSTR(full_string,360,2)) AS LSADC,
    trim(SUBSTR(full_string,362,1)) AS PARTFLAG,
    trim(SUBSTR(full_string,363,6)) AS RESERVE3,
    trim(SUBSTR(full_string,369,5)) AS UGA,
    trim(SUBSTR(full_string,374,8)) AS STATENS,
    trim(SUBSTR(full_string,382,8)) AS COUNTYNS,
    trim(SUBSTR(full_string,390,8)) AS COUSUBNS,
    trim(SUBSTR(full_string,398,8)) AS PLACENS,
    trim(SUBSTR(full_string,406,8)) AS CONCITNS,
    trim(SUBSTR(full_string,414,8)) AS AIANHHNS,
    trim(SUBSTR(full_string,422,8)) AS AITSNS,
    trim(SUBSTR(full_string,430,8)) AS ANRCNS,
    trim(SUBSTR(full_string,438,8)) AS SUBMCDNS,
    trim(SUBSTR(full_string,446,2)) AS CD113,
    trim(SUBSTR(full_string,448,2)) AS CD114,
    trim(SUBSTR(full_string,450,2)) AS CD115,
    trim(SUBSTR(full_string,452,3)) AS SLDU2,
    trim(SUBSTR(full_string,455,3)) AS SLDU3,
    trim(SUBSTR(full_string,458,3)) AS SLDU4,
    trim(SUBSTR(full_string,461,3)) AS SLDL2,
    trim(SUBSTR(full_string,464,3)) AS SLDL3,
    trim(SUBSTR(full_string,467,3)) AS SLDL4,
    trim(SUBSTR(full_string,470,2)) AS AIANHHSC,
    trim(SUBSTR(full_string,472,2)) AS CSASC,
    trim(SUBSTR(full_string,474,2)) AS CNECTASC,
    trim(SUBSTR(full_string,476,1)) AS MEMI,
    trim(SUBSTR(full_string,477,1)) AS NMEMI,
    trim(SUBSTR(full_string,478,5)) AS PUMA,
    trim(SUBSTR(full_string,483,18)) AS RESERVED,
    trim(SUBSTR(full_string,28,2) || SUBSTR(full_string,46,5)) AS GEOID
FROM ghr_bulk;

# Export GHR to CSV
# sqlite3 geo.db
.headers on
.mode csv
.output tmp/us2010.ur1/usgeo2010.ur1.csv
SELECT * FROM ghr_txt;
.output stdout

# These tables are no longer needed and should not be used
DROP TABLE ghr_bulk;
DROP TABLE ghr_txt;

.quit

# If following steps sequentially (strongly recommended):
cd tmp

#______________________________________________________________________
#
# STEP 2: UNICODE CONVERSION
#______________________________________________________________________
#

# Convert files from ISO-8859-15 to UTF-8:
# dir: intertwine/platform/data/geos/tmp
iconv -f ISO-8859-15 -t UTF-8 Gaz_places_national.txt > Gaz_places_national_utf-8.txt
mkdir us2010.ur1.utf-8
iconv -f ISO-8859-15 -t UTF-8 us2010.ur1/usgeo2010.ur1.csv > us2010.ur1.utf-8/usgeo2010.ur1.utf-8.csv
iconv -f ISO-8859-15 -t UTF-8 us2010.ur1/us000022010.ur1 > us2010.ur1.utf-8/us000022010.ur1.utf-8.csv

# Create copies without first row as we create the table first to handle non-text types:
# dir: intertwine/platform/data/geos/tmp
tail -n +2 "Gaz_places_national_utf-8.txt" > "Gaz_places_national_utf-8.txt.tmp"
cd us2010.ur1.utf-8
tail -n +2 "usgeo2010.ur1.utf-8.csv" > "usgeo2010.ur1.utf-8.csv.tmp"
tail -n +2 "us000022010.ur1.utf-8.csv" > "us000022010.ur1.utf-8.csv.tmp"

# If following steps sequentially (strongly recommended):
cd ../..

#______________________________________________________________________
#
# STEP 3: PREPARE TABLES FOR UPLOAD
#______________________________________________________________________
#

# Create tables for those that contain non-text types
# dir: intertwine/platform/data/geos

sqlite3 geo.db

CREATE TABLE place(
    "USPS" TEXT,
    "GEOID" TEXT,
    "ANSICODE" TEXT,
    "NAME" TEXT,
    "LSAD_CODE" TEXT,
    "FUNCSTAT" TEXT,
    "POP10" INTEGER,
    "HU10" INTEGER,
    "ALAND" INTEGER,
    "AWATER" INTEGER,
    "ALAND_SQMI" REAL,
    "AWATER_SQMI" REAL,
    "INTPTLAT" REAL,
    "INTPTLONG" REAL
);

CREATE TABLE ghr(
    "FILEID" TEXT,
    "STUSAB" TEXT,
    "SUMLEV" TEXT,
    "GEOCOMP" TEXT,
    "CHARITER" TEXT,
    "CIFSN" TEXT,
    "LOGRECNO" INTEGER,
    "REGION" TEXT,
    "DIVISION" TEXT,
    "STATEFP" TEXT,
    "COUNTYFP" TEXT,
    "COUNTYCC" TEXT,
    "COUNTYSC" TEXT,
    "COUSUB" TEXT,
    "COUSUBCC" TEXT,
    "COUSUBSC" TEXT,
    "PLACEFP" TEXT,
    "PLACECC" TEXT,
    "PLACESC" TEXT,
    "TRACT" TEXT,
    "BLKGRP" TEXT,
    "BLOCK" TEXT,
    "IUC" TEXT,
    "CONCIT" TEXT,
    "CONCITCC" TEXT,
    "CONCITSC" TEXT,
    "AIANHH" TEXT,
    "AIANHHFP" TEXT,
    "AIANHHCC" TEXT,
    "AIHHTLI" TEXT,
    "AITSCE" TEXT,
    "AITS" TEXT,
    "AITSCC" TEXT,
    "TTRACT" TEXT,
    "TBLKGRP" TEXT,
    "ANRC" TEXT,
    "ANRCCC" TEXT,
    "CBSA" TEXT,
    "CBSASC" TEXT,
    "METDIV" TEXT,
    "CSA" TEXT,
    "NECTA" TEXT,
    "NECTASC" TEXT,
    "NECTADIV" TEXT,
    "CNECTA" TEXT,
    "CBSAPCI" TEXT,
    "NECTAPCI" TEXT,
    "UA" TEXT,
    "UASC" TEXT,
    "UATYPE" TEXT,
    "UR" TEXT,
    "CD" TEXT,
    "SLDU" TEXT,
    "SLDL" TEXT,
    "VTD" TEXT,
    "VTDI" TEXT,
    "RESERVE2" TEXT,
    "ZCTA5" TEXT,
    "SUBMCD" TEXT,
    "SUBMCDCC" TEXT,
    "SDELM" TEXT,
    "SDSEC" TEXT,
    "SDUNI" TEXT,
    "AREALAND" INTEGER,
    "AREAWATR" INTEGER,
    "NAME" TEXT,
    "FUNCSTAT" TEXT,
    "GCUNI" TEXT,
    "POP100" INTEGER,
    "HU100" INTEGER,
    "INTPTLAT" FLOAT,
    "INTPTLON" FLOAT,
    "LSADC" TEXT,
    "PARTFLAG" TEXT,
    "RESERVE3" TEXT,
    "UGA" TEXT,
    "STATENS" TEXT,
    "COUNTYNS" TEXT,
    "COUSUBNS" TEXT,
    "PLACENS" TEXT,
    "CONCITNS" TEXT,
    "AIANHHNS" TEXT,
    "AITSNS" TEXT,
    "ANRCNS" TEXT,
    "SUBMCDNS" TEXT,
    "CD113" TEXT,
    "CD114" TEXT,
    "CD115" TEXT,
    "SLDU2" TEXT,
    "SLDU3" TEXT,
    "SLDU4" TEXT,
    "SLDL2" TEXT,
    "SLDL3" TEXT,
    "SLDL4" TEXT,
    "AIANHHSC" TEXT,
    "CSASC" TEXT,
    "CNECTASC" TEXT,
    "MEMI" TEXT,
    "NMEMI" TEXT,
    "PUMA" TEXT,
    "RESERVED" TEXT,
    "GEOID" TEXT
);

CREATE TABLE f02(
    "FILEID" TEXT,
    "STUSAB" TEXT,
    "CHARITER" TEXT,
    "CIFSN" TEXT,
    "LOGRECNO" INTEGER,
    "P0020001" INTEGER,
    "P0020002" INTEGER,
    "P0020003" INTEGER,
    "P0020004" INTEGER,
    "P0020005" INTEGER,
    "P0020006" INTEGER
);

#______________________________________________________________________
#
# STEP 4: UPLOAD DATA
#______________________________________________________________________
#

# dir: intertwine/platform/data/geos
# sqlite3 geo.db

.separator "\t"
.import tmp/Gaz_places_national_utf-8.txt.tmp place

.separator ","
.import national_county.txt county
.import cbsa.csv cbsa
.import lsad.csv lsad
.import tmp/us2010.ur1.utf-8/usgeo2010.ur1.utf-8.csv.tmp ghr
.import tmp/us2010.ur1.utf-8/us000022010.ur1.utf-8.csv.tmp f02

.separator "|"
.import state.txt state











.headers on
.mode csv
.output ur1_us_ghr_070.csv
SELECT * FROM ur1_us_ghr WHERE SUMLEV = "070";
.output stdout

.headers on
.mode csv
.output ur1_us_f02_070.csv
SELECT f.FILEID, f.STUSAB, f.CHARITER, f.CIFSN, f.LOGRECNO, f.P0020001,
    f.P0020002, f.P0020003, f.P0020004, f.P0020005, f.P0020006
    FROM ur1_us_f02 AS f
    LEFT OUTER JOIN ur1_us_ghr AS g ON f.LOGRECNO = g.LOGRECNO
    WHERE g.SUMLEV = "070";
.output stdout

.headers on
.mode csv
.output ur1_ghr_f02_austin.csv
SELECT * FROM ur1_us_ghr
    LEFT OUTER JOIN ur1_us_f02 ON ur1_us_ghr.LOGRECNO = ur1_us_f02.LOGRECNO
    WHERE PLACE = "05000";
.output stdout

.headers on
.mode csv
.output ur1_ghr_f02_070_tx.csv
SELECT * FROM ur1_us_ghr
    LEFT OUTER JOIN ur1_us_f02 ON ur1_us_ghr.LOGRECNO = ur1_us_f02.LOGRECNO
    WHERE ur1_us_ghr.SUMLEV = "070" AND ur1_us_ghr.STUSAB = "TX";
.output stdout

.headers on
.mode csv
.output ur1_tx_ghr_f02_100_austin.csv
SELECT * FROM ur1_tx_ghr
    LEFT OUTER JOIN ur1_tx_f02 ON ur1_tx_ghr.LOGRECNO = ur1_tx_f02.LOGRECNO
    WHERE ur1_tx_ghr.SUMLEV = "100" AND PLACE = "05000";
.output stdout

.headers on
.mode csv
.output ur1_us_ghr_f02_070.csv
SELECT * FROM ur1_us_ghr
    LEFT OUTER JOIN ur1_us_f02 ON ur1_us_ghr.LOGRECNO = ur1_us_f02.LOGRECNO
    LEFT OUTER JOIN state ON ur1_us_ghr.STATE = state.STATE_FIPS_CODE
    LEFT OUTER JOIN cbsa ON ur1_us_ghr.CBSA = cbsa.CBSA_CODE
    LEFT OUTER JOIN county ON ur1_us_ghr.STATE = county.STATEFP AND ur1_us_ghr.COUNTY = county.COUNTYFP
    WHERE geo_ur1.SUMLEV = "070";
.output stdout

