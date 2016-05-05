
2010 Census Summary File 1 Technical Documentation:
http://www.census.gov/prod/cen2010/doc/sf1.pdf

TABLE           FILE                        FORMAT  SOURCE
ur1_us_ghr_070  ur1_us_ghr_070.csv          ","     ur1_us_ghr
ur1_us_f02_070  ur1_us_f02_070.csv          ","     ur1_us_f02
ur1_us_ghr      us2010.ur1/usgeo2010.ur1    fixed   http://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National
ur1_us_f02      us2010.ur1/us000022010.ur1  ","     http://www2.census.gov/census_2010/04-Summary_File_1/Urban_Rural_Update/National
state           state.txt                   "|"     https://www.census.gov/geo/reference/ansi_statetables.html
cbsa            cbsa.csv                    ","     https://www.census.gov/population/metro/files/lists/2013/List1.xls
county          national_county.txt         "\t"    https://www.census.gov/geo/reference/codes/cou.html
place           Gaz_places_national.txt     "\t"    https://www.census.gov/geo/maps-data/data/gazetteer2010.html
lsad            lsad.csv                    ","     https://www.census.gov/geo/reference/lsad.html

KEY
ur1     Urban Rural Update 1
ghr     Geographic Header Record
070     SUMLEV = 070, the Summary Level for: State-County-County Subdivision-Place/Remainder
cbsa    Core Based Statistical Area, a general term that applies to metropolitan and micropolitan statistical areas
place   Census term for an incorporated place or a census designated place (CDP)
lsad    Legal/Statistical Area Description (city, town, borough, CDP, etc.)
