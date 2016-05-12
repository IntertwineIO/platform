SOURCES

TABLE           FILE                        FORMAT  SOURCE
ur1_us_ghr      us2010.ur1/usgeo2010.ur1    fixed   http://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National
ur1_us_f02      us2010.ur1/us000022010.ur1  ","     http://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National
ghr             ur1_us_ghr_070.csv          ","     ur1_us_ghr
f02             ur1_us_f02_070.csv          ","     ur1_us_f02
state           state.txt                   "|"     https://www.census.gov/geo/reference/ansi_statetables.html
cbsa            cbsa.csv                    ","     https://www.census.gov/population/metro/files/lists/2013/List1.xls
county          national_county.txt         "\t"    https://www.census.gov/geo/reference/codes/cou.html
place           Gaz_places_national.txt     "\t"    https://www.census.gov/geo/maps-data/data/gazetteer2010.html
lsad            lsad.csv                    ","     https://www.census.gov/geo/reference/lsad.html
__________

KEY

ur1     Urban Rural Update 1
us      United States National File (vs. individual states)
ghr     Geographic Header Record
f02     File 02, which contains urban vs. rural population counts
070     SUMLEV = 070, the Summary Level for: State-County-County Subdivision-Place/Remainder
cbsa    Core Based Statistical Area, a general term that applies to metropolitan and micropolitan statistical areas
place   Census term for an incorporated place or a census designated place (CDP)
lsad    Legal/Statistical Area Description (city, town, borough, CDP, etc.)
__________

REFERENCES

2010 Census Summary File 1 Technical Documentation:
http://www.census.gov/prod/cen2010/doc/sf1.pdf

Individual State Descriptions: 2012
https://www2.census.gov/govs/cog/2012isd.pdf

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
    SUBSTR(full_string,1,6) AS FILEID,
    SUBSTR(full_string,7,2) AS STUSAB,
    SUBSTR(full_string,9,3) AS SUMLEV,
    SUBSTR(full_string,12,2) AS GEOCOMP,
    SUBSTR(full_string,14,3) AS CHARITER,
    SUBSTR(full_string,17,2) AS CIFSN,
    SUBSTR(full_string,19,7) AS LOGRECNO,
    SUBSTR(full_string,26,1) AS REGION,
    SUBSTR(full_string,27,1) AS DIVISION,
    SUBSTR(full_string,28,2) AS STATE,
    SUBSTR(full_string,30,3) AS COUNTY,
    SUBSTR(full_string,33,2) AS COUNTYCC,
    SUBSTR(full_string,35,2) AS COUNTYSC,
    SUBSTR(full_string,37,5) AS COUSUB,
    SUBSTR(full_string,42,2) AS COUSUBCC,
    SUBSTR(full_string,44,2) AS COUSUBSC,
    SUBSTR(full_string,46,5) AS PLACE,
    SUBSTR(full_string,51,2) AS PLACECC,
    SUBSTR(full_string,53,2) AS PLACESC,
    SUBSTR(full_string,55,6) AS TRACT,
    SUBSTR(full_string,61,1) AS BLKGRP,
    SUBSTR(full_string,62,4) AS BLOCK,
    SUBSTR(full_string,66,2) AS IUC,
    SUBSTR(full_string,68,5) AS CONCIT,
    SUBSTR(full_string,73,2) AS CONCITCC,
    SUBSTR(full_string,75,2) AS CONCITSC,
    SUBSTR(full_string,77,4) AS AIANHH,
    SUBSTR(full_string,81,5) AS AIANHHFP,
    SUBSTR(full_string,86,2) AS AIANHHCC,
    SUBSTR(full_string,88,1) AS AIHHTLI,
    SUBSTR(full_string,89,3) AS AITSCE,
    SUBSTR(full_string,92,5) AS AITS,
    SUBSTR(full_string,97,2) AS AITSCC,
    SUBSTR(full_string,99,6) AS TTRACT,
    SUBSTR(full_string,105,1) AS TBLKGRP,
    SUBSTR(full_string,106,5) AS ANRC,
    SUBSTR(full_string,111,2) AS ANRCCC,
    SUBSTR(full_string,113,5) AS CBSA,
    SUBSTR(full_string,118,2) AS CBSASC,
    SUBSTR(full_string,120,5) AS METDIV,
    SUBSTR(full_string,125,3) AS CSA,
    SUBSTR(full_string,128,5) AS NECTA,
    SUBSTR(full_string,133,2) AS NECTASC,
    SUBSTR(full_string,135,5) AS NECTADIV,
    SUBSTR(full_string,140,3) AS CNECTA,
    SUBSTR(full_string,143,1) AS CBSAPCI,
    SUBSTR(full_string,144,1) AS NECTAPCI,
    SUBSTR(full_string,145,5) AS UA,
    SUBSTR(full_string,150,2) AS UASC,
    SUBSTR(full_string,152,1) AS UATYPE,
    SUBSTR(full_string,153,1) AS UR,
    SUBSTR(full_string,154,2) AS CD,
    SUBSTR(full_string,156,3) AS SLDU,
    SUBSTR(full_string,159,3) AS SLDL,
    SUBSTR(full_string,162,6) AS VTD,
    SUBSTR(full_string,168,1) AS VTDI,
    SUBSTR(full_string,169,3) AS RESERVE2,
    SUBSTR(full_string,172,5) AS ZCTA5,
    SUBSTR(full_string,177,5) AS SUBMCD,
    SUBSTR(full_string,182,2) AS SUBMCDCC,
    SUBSTR(full_string,184,5) AS SDELM,
    SUBSTR(full_string,189,5) AS SDSEC,
    SUBSTR(full_string,194,5) AS SDUNI,
    SUBSTR(full_string,199,14) AS AREALAND,
    SUBSTR(full_string,213,14) AS AREAWATR,
    SUBSTR(full_string,227,90) AS NAME,
    SUBSTR(full_string,317,1) AS FUNCSTAT,
    SUBSTR(full_string,318,1) AS GCUNI,
    SUBSTR(full_string,319,9) AS POP100,
    SUBSTR(full_string,328,9) AS HU100,
    SUBSTR(full_string,337,11) AS INTPTLAT,
    SUBSTR(full_string,348,12) AS INTPTLON,
    SUBSTR(full_string,360,2) AS LSADC,
    SUBSTR(full_string,362,1) AS PARTFLAG,
    SUBSTR(full_string,363,6) AS RESERVE3,
    SUBSTR(full_string,369,5) AS UGA,
    SUBSTR(full_string,374,8) AS STATENS,
    SUBSTR(full_string,382,8) AS COUNTYNS,
    SUBSTR(full_string,390,8) AS COUSUBNS,
    SUBSTR(full_string,398,8) AS PLACENS,
    SUBSTR(full_string,406,8) AS CONCITNS,
    SUBSTR(full_string,414,8) AS AIANHHNS,
    SUBSTR(full_string,422,8) AS AITSNS,
    SUBSTR(full_string,430,8) AS ANRCNS,
    SUBSTR(full_string,438,8) AS SUBMCDNS,
    SUBSTR(full_string,446,2) AS CD113,
    SUBSTR(full_string,448,2) AS CD114,
    SUBSTR(full_string,450,2) AS CD115,
    SUBSTR(full_string,452,3) AS SLDU2,
    SUBSTR(full_string,455,3) AS SLDU3,
    SUBSTR(full_string,458,3) AS SLDU4,
    SUBSTR(full_string,461,3) AS SLDL2,
    SUBSTR(full_string,464,3) AS SLDL3,
    SUBSTR(full_string,467,3) AS SLDL4,
    SUBSTR(full_string,470,2) AS AIANHHSC,
    SUBSTR(full_string,472,2) AS CSASC,
    SUBSTR(full_string,474,2) AS CNECTASC,
    SUBSTR(full_string,476,1) AS MEMI,
    SUBSTR(full_string,477,1) AS NMEMI,
    SUBSTR(full_string,478,5) AS PUMA,
    SUBSTR(full_string,483,18) AS RESERVED
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
    "LONG_NAME" TEXT,
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
    "STATE" TEXT,
    "COUNTY" TEXT,
    "COUNTYCC" TEXT,
    "COUNTYSC" TEXT,
    "COUSUB" TEXT,
    "COUSUBCC" TEXT,
    "COUSUBSC" TEXT,
    "PLACE" TEXT,
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
    "RESERVED" TEXT
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


