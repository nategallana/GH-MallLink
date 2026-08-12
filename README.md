# GH-MallLink
Green Hills Mall Linking system - connected to the cloud using Python and C# 


This project is used for processing EOD reports for the mall using their requirements. 
Collecting the data from our client (FRANKIES) that is located in Green Hills.

Used Python for reading, fetching, and converting the Cloud data to SQL.
Used C# for reading, fetching, and converting the Paradox database values to SQL. 
Used SQLite for the database. 

If the SQLite database were deleted, the system will automatically create a new one after processing an EOD date. 
Auto export of .SALE file as well for both Paradox and Cloud values.   
