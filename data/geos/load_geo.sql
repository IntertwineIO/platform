
.separator "|"
.import state.txt state

.separator ","
.import national_county.txt county

.separator "\t"
.import Gaz_places_national.txt place

.separator ","
.import cbsa.csv cbsa

.separator ","
.import lsad.csv lsad

.separator ","
.import ur1_us_ghr_070.csv ur1_us_ghr_070

.separator ","
.import ur1_us_f02_070.csv ur1_us_f02_070


CREATE TABLE ur1_us_ghr_bulk (full_string CHAR);
.import us2010.ur1/usgeo2010.ur1 ur1_us_ghr_bulk


CREATE TABLE ur1_us_ghr AS
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
FROM ur1_us_ghr_bulk;


CREATE TABLE ur1_us_ghr_austin AS
SELECT * FROM ur1_us_ghr WHERE PLACE="05000";


CREATE TABLE ur1_us_f01(FILEID, STUSAB, CHARITER, CIFSN, LOGRECNO, P0010001);
.mode csv
.import us2010.ur1/us000012010.ur1 ur1_us_f01

CREATE TABLE ur1_us_f02(FILEID, STUSAB, CHARITER, CIFSN, LOGRECNO, P0020001, P0020002, P0020003, P0020004, P0020005, P0020006);
.mode csv
.import us2010.ur1/us000022010.ur1 ur1_us_f02

CREATE TABLE ur1_us_f03(
    FILEID,
    STUSAB,
    CHARITER,
    CIFSN,
    LOGRECNO,
    P0030001,
    P0030002,
    P0030003,
    P0030004,
    P0030005,
    P0030006,
    P0030007,
    P0030008,
    P0040001,
    P0040002,
    P0040003,
    P0050001,
    P0050002,
    P0050003,
    P0050004,
    P0050005,
    P0050006,
    P0050007,
    P0050008,
    P0050009,
    P0050010,
    P0050011,
    P0050012,
    P0050013,
    P0050014,
    P0050015,
    P0050016,
    P0050017,
    P0060001,
    P0060002,
    P0060003,
    P0060004,
    P0060005,
    P0060006,
    P0060007,
    P0070001,
    P0070002,
    P0070003,
    P0070004,
    P0070005,
    P0070006,
    P0070007,
    P0070008,
    P0070009,
    P0070010,
    P0070011,
    P0070012,
    P0070013,
    P0070014,
    P0070015,
    P0080001,
    P0080002,
    P0080003,
    P0080004,
    P0080005,
    P0080006,
    P0080007,
    P0080008,
    P0080009,
    P0080010,
    P0080011,
    P0080012,
    P0080013,
    P0080014,
    P0080015,
    P0080016,
    P0080017,
    P0080018,
    P0080019,
    P0080020,
    P0080021,
    P0080022,
    P0080023,
    P0080024,
    P0080025,
    P0080026,
    P0080027,
    P0080028,
    P0080029,
    P0080030,
    P0080031,
    P0080032,
    P0080033,
    P0080034,
    P0080035,
    P0080036,
    P0080037,
    P0080038,
    P0080039,
    P0080040,
    P0080041,
    P0080042,
    P0080043,
    P0080044,
    P0080045,
    P0080046,
    P0080047,
    P0080048,
    P0080049,
    P0080050,
    P0080051,
    P0080052,
    P0080053,
    P0080054,
    P0080055,
    P0080056,
    P0080057,
    P0080058,
    P0080059,
    P0080060,
    P0080061,
    P0080062,
    P0080063,
    P0080064,
    P0080065,
    P0080066,
    P0080067,
    P0080068,
    P0080069,
    P0080070,
    P0080071,
    P0090001,
    P0090002,
    P0090003,
    P0090004,
    P0090005,
    P0090006,
    P0090007,
    P0090008,
    P0090009,
    P0090010,
    P0090011,
    P0090012,
    P0090013,
    P0090014,
    P0090015,
    P0090016,
    P0090017,
    P0090018,
    P0090019,
    P0090020,
    P0090021,
    P0090022,
    P0090023,
    P0090024,
    P0090025,
    P0090026,
    P0090027,
    P0090028,
    P0090029,
    P0090030,
    P0090031,
    P0090032,
    P0090033,
    P0090034,
    P0090035,
    P0090036,
    P0090037,
    P0090038,
    P0090039,
    P0090040,
    P0090041,
    P0090042,
    P0090043,
    P0090044,
    P0090045,
    P0090046,
    P0090047,
    P0090048,
    P0090049,
    P0090050,
    P0090051,
    P0090052,
    P0090053,
    P0090054,
    P0090055,
    P0090056,
    P0090057,
    P0090058,
    P0090059,
    P0090060,
    P0090061,
    P0090062,
    P0090063,
    P0090064,
    P0090065,
    P0090066,
    P0090067,
    P0090068,
    P0090069,
    P0090070,
    P0090071,
    P0090072,
    P0090073
    );
.mode csv
.import us2010.ur1/us000032010.sf1 ur1_us_f03


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

