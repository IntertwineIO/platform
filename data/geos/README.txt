SOURCES

TABLE     FILE                               SEP   SOURCE
ghr_bulk  usgeo2010.ur1                      fix   https://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National/us2010.ur1.zip
ghr_txt   n/a (created in database)          n/a   ghr_bulk
ghr       usgeo2010.ur1.utf-8.csv.tmp        ','   Exported from ghr_txt, then converted to utf-8 and headers removed
f02       us000022010.ur1.utf-8.csv.tmp      ','   Same as usgeo2010.ur1, then converted to utf-8 (no headers to remove)
ghrp      n/a (created in database)          n/a   ghr and f02
state     state.txt.tmp                      '|'   https://www2.census.gov/geo/docs/reference/state.txt
cbsa      cbsa_utf-8.csv.tmp                 ','   https://www.census.gov/population/metro/files/lists/2013/List1.xls
county    national_county.txt.tmp            ','   https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt
place     Gaz_places_national_utf-8.txt.tmp  '\t'  https://www2.census.gov/geo/docs/maps-data/data/gazetteer/Gaz_places_national.zip (then converted to utf-8 and headers removed)
lsad      lsad.csv.tmp                       ','   https://www.census.gov/geo/reference/lsad.html (copied from html table)
geoclass  geoclass.csv.tmp                   ','   http://www.census.gov/prod/cen2010/doc/sf1.pdf#165 (55-2 copied from pdf)
__________

KEY

us        United States National File (vs. individual states)
2010      Census 2010
ur1       Urban Rural Update 1 (released in 2012)
ghr       Geographic Header Record
f02       File 02, which contains urban vs. rural population counts
cbsa      Core Based Statistical Area, a general term that applies to metropolitan and micropolitan statistical areas
place     Census term for an incorporated place or a census designated place (CDP)
lsad      Legal/Statistical Area Description (city, town, borough, CDP, etc.)
geoclass  FIPS code describing legal, statistical, governmental, and/or relationship status of a geo
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

# Go to intertwine/platform/data/geos
cd ..

#______________________________________________________________________
#
# STEP 1: PRE-PROCESS GEOGRAPHIC HEADER RECORD (GHR) FILE
#______________________________________________________________________
#
# dir: intertwine/platform/data/geos

# Load Geographic Header Record (GHR)
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

# Go to intertwine/platform/data/geos/tmp
cd tmp

#______________________________________________________________________
#
# STEP 2: UNICODE CONVERSION AND HEADER REMOVAL
#______________________________________________________________________
#
# dir: intertwine/platform/data/geos/tmp

# Convert files from ISO-8859-15 to UTF-8:
../../../scripts/encode-file.py -e iso-8859-1 ../cbsa.csv > cbsa_utf-8.csv
../../../scripts/encode-file.py -e iso-8859-1 Gaz_places_national.txt > Gaz_places_national_utf-8.txt

mkdir us2010.ur1.utf-8
../../../scripts/encode-file.py -e iso-8859-1 us2010.ur1/usgeo2010.ur1.csv > us2010.ur1.utf-8/usgeo2010.ur1.utf-8.csv
../../../scripts/encode-file.py -e iso-8859-1 us2010.ur1/us000022010.ur1 > us2010.ur1.utf-8/us000022010.ur1.utf-8.csv

# Create copies without first row as we create the table first to handle non-text types:
# dir: intertwine/platform/data/geos
tail -n +2 "../state.txt" > "state.txt.tmp"
tail -n +2 "../national_county.txt" > "national_county.txt.tmp"
tail -n +2 "../lsad.csv" > "lsad.csv.tmp"
tail -n +2 "../geoclass.csv" > "geoclass.csv.tmp"

tail -n +2 "cbsa_utf-8.csv" > "cbsa_utf-8.csv.tmp"
tail -n +2 "Gaz_places_national_utf-8.txt" > "Gaz_places_national_utf-8.txt.tmp"

cd us2010.ur1.utf-8
tail -n +2 "usgeo2010.ur1.utf-8.csv" > "usgeo2010.ur1.utf-8.csv.tmp"
cp "us000022010.ur1.utf-8.csv" "us000022010.ur1.utf-8.csv.tmp"
# Note: "us000022010.ur1.utf-8.csv" lacks a header row, so cp instead of tail

# Go to intertwine/platform/data/geos
cd ../..

#______________________________________________________________________
#
# STEP 3: CREATE TABLE SCHEMAS
#______________________________________________________________________
#

# Create table schemas to allow column renaming and non-text types
# dir: intertwine/platform/data/geos

sqlite3 geo.db

CREATE TABLE state(
    "statefp" TEXT,
    "stusps" TEXT,
    "name" TEXT,
    "statens" TEXT
);

CREATE TABLE cbsa(
    "cbsa_code" TEXT,
    "metro_division_code" TEXT,
    "csa_code" TEXT,
    "cbsa_name" TEXT,
    "cbsa_type" TEXT,
    "metro_division_name" TEXT,
    "csa_name" TEXT,
    "county_name" TEXT,
    "state_name" TEXT,
    "statefp" TEXT,
    "countyfp" TEXT,
    "county_type" TEXT
);

CREATE TABLE county(
    "stusps" TEXT,
    "statefp" TEXT,
    "countyfp" TEXT,
    "name" TEXT,
    "geoclassfp" TEXT
);

CREATE TABLE place(
    "stusps" TEXT,
    "geoid" TEXT,
    "ansicode" TEXT,
    "name" TEXT,
    "lsad_code" TEXT,
    "funcstat" TEXT,
    "pop10" INTEGER,
    "hu10" INTEGER,
    "aland" INTEGER,
    "awater" INTEGER,
    "aland_sqmi" REAL,
    "awater_sqmi" REAL,
    "intptlat" REAL,
    "intptlong" REAL
);

CREATE TABLE lsad(
    "lsad_code" TEXT,
    "display" TEXT,
    "geo_entity_type" TEXT
);

CREATE TABLE geoclass(
    "geoclassfp" TEXT,
    "category" TEXT,
    "name" TEXT,
    "description" TEXT
);

CREATE TABLE ghr(
    "fileid" TEXT,
    "stusab" TEXT,
    "sumlev" TEXT,
    "geocomp" TEXT,
    "chariter" TEXT,
    "cifsn" TEXT,
    "logrecno" INTEGER,
    "region" TEXT,
    "division" TEXT,
    "statefp" TEXT,
    "countyfp" TEXT,
    "countycc" TEXT,
    "countysc" TEXT,
    "cousub" TEXT,
    "cousubcc" TEXT,
    "cousubsc" TEXT,
    "placefp" TEXT,
    "placecc" TEXT,
    "placesc" TEXT,
    "tract" TEXT,
    "blkgrp" TEXT,
    "block" TEXT,
    "iuc" TEXT,
    "concit" TEXT,
    "concitcc" TEXT,
    "concitsc" TEXT,
    "aianhh" TEXT,
    "aianhhfp" TEXT,
    "aianhhcc" TEXT,
    "aihhtli" TEXT,
    "aitsce" TEXT,
    "aits" TEXT,
    "aitscc" TEXT,
    "ttract" TEXT,
    "tblkgrp" TEXT,
    "anrc" TEXT,
    "anrccc" TEXT,
    "cbsa" TEXT,
    "cbsasc" TEXT,
    "metdiv" TEXT,
    "csa" TEXT,
    "necta" TEXT,
    "nectasc" TEXT,
    "nectadiv" TEXT,
    "cnecta" TEXT,
    "cbsapci" TEXT,
    "nectapci" TEXT,
    "ua" TEXT,
    "uasc" TEXT,
    "uatype" TEXT,
    "ur" TEXT,
    "cd" TEXT,
    "sldu" TEXT,
    "sldl" TEXT,
    "vtd" TEXT,
    "vtdi" TEXT,
    "reserve2" TEXT,
    "zcta5" TEXT,
    "submcd" TEXT,
    "submcdcc" TEXT,
    "sdelm" TEXT,
    "sdsec" TEXT,
    "sduni" TEXT,
    "arealand" INTEGER,
    "areawatr" INTEGER,
    "name" TEXT,
    "funcstat" TEXT,
    "gcuni" TEXT,
    "pop100" INTEGER,
    "hu100" INTEGER,
    "intptlat" FLOAT,
    "intptlon" FLOAT,
    "lsadc" TEXT,
    "partflag" TEXT,
    "reserve3" TEXT,
    "uga" TEXT,
    "statens" TEXT,
    "countyns" TEXT,
    "cousubns" TEXT,
    "placens" TEXT,
    "concitns" TEXT,
    "aianhhns" TEXT,
    "aitsns" TEXT,
    "anrcns" TEXT,
    "submcdns" TEXT,
    "cd113" TEXT,
    "cd114" TEXT,
    "cd115" TEXT,
    "sldu2" TEXT,
    "sldu3" TEXT,
    "sldu4" TEXT,
    "sldl2" TEXT,
    "sldl3" TEXT,
    "sldl4" TEXT,
    "aianhhsc" TEXT,
    "csasc" TEXT,
    "cnectasc" TEXT,
    "memi" TEXT,
    "nmemi" TEXT,
    "puma" TEXT,
    "reserved" TEXT,
    "geoid" TEXT
);

CREATE TABLE f02(
    "fileid" TEXT,
    "stusab" TEXT,
    "chariter" TEXT,
    "cifsn" TEXT,
    "logrecno" INTEGER,
    "p0020001" INTEGER,
    "p0020002" INTEGER,
    "p0020003" INTEGER,
    "p0020004" INTEGER,
    "p0020005" INTEGER,
    "p0020006" INTEGER
);

#______________________________________________________________________
#
# STEP 4: UPLOAD DATA
#______________________________________________________________________
#

# dir: intertwine/platform/data/geos
# sqlite3 geo.db

.separator "|"
.import tmp/state.txt.tmp state

.separator "\t"
.import tmp/Gaz_places_national_utf-8.txt.tmp place

.separator ","
.import tmp/national_county.txt.tmp county
.import tmp/cbsa_utf-8.csv.tmp cbsa
.import tmp/lsad.csv.tmp lsad
.import tmp/geoclass.csv.tmp geoclass
.import tmp/us2010.ur1.utf-8/usgeo2010.ur1.utf-8.csv.tmp ghr
.import tmp/us2010.ur1.utf-8/us000022010.ur1.utf-8.csv.tmp f02

#______________________________________________________________________
#
# STEP 5: POST-UPLOAD PROCESSING
#______________________________________________________________________
#

# dir: intertwine/platform/data/geos
# sqlite3 geo.db
CREATE TABLE ghrp AS
SELECT * FROM ghr LEFT OUTER JOIN f02 ON ghr.LOGRECNO = f02.LOGRECNO;
