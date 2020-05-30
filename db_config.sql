drop database Covid_secure;

create database Covid_secure;

use Covid_secure;

create table User_Profile (
	UserID varchar(32),
	firstName varchar(30),
	lastName varchar(30),
	homeLat float(53),
	homeLong float(53),
	flag int(1),
	flagged_at timestamp,
	primary key (UserID)
);

create table Login_Credentials (
	UserID varchar(32),
	password varchar(32),
	primary key (UserID),
	foreign key (UserID) references User_Profile (UserID) on delete cascade on update cascade
);

create table Last_Location (
	LocationID int(11),
	UserID varchar(32),
	lastLat float(53),
	lastLong float(53),
	updated_at timestamp,
	foreign key (UserID) references User_Profile (UserID) on delete cascade on update cascade
);