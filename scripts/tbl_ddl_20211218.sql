alter table tbl_route_info add maxDistance DOUBLE(10,2) ;
alter table tbl_route_info add maxDuration DOUBLE(10,2) ;
alter table tbl_route_info add vehicleType TINYINT(1) NOT NULL  DEFAULT 0;