alter table tbl_route_info add maxDistance DOUBLE(10,2) ;
alter table tbl_route_info add maxDuration DOUBLE(10,2) ;
alter table tbl_route_info add vehicleType TINYINT(1) NOT NULL  DEFAULT 0;


CREATE TABLE `tbl_station_style` (
  `style` text NOT NULL COMMENT '样式',
  `remark` varchar(255) DEFAULT NULL COMMENT '备注',
  `createTime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updateTime` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;