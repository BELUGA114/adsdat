"""运行期构建 v2ray/xray geosite.dat 的最小 protobuf schema，避免依赖 protoc。

同时提供解析(load)与序列化(dump)，供 build.py 编译与回读校验复用。
geosite 的 Domain.Type 枚举：Plain(keyword)=0, Regex=1, Domain=2, Full=3。
"""
from __future__ import annotations

from google.protobuf import descriptor_pb2 as dpb
from google.protobuf import descriptor_pool, message_factory

TYPE_TO_NAME: dict[int, str] = {0: "keyword", 1: "regexp", 2: "domain", 3: "full"}
NAME_TO_TYPE: dict[str, int] = {"keyword": 0, "plain": 0, "regexp": 1, "domain": 2, "full": 3}


def _geositelist_cls():
    fdp = dpb.FileDescriptorProto()
    fdp.name = "geosite.proto"
    fdp.package = "router"
    fdp.syntax = "proto3"

    dom = fdp.message_type.add()
    dom.name = "Domain"
    et = dom.enum_type.add()
    et.name = "Type"
    for i, n in enumerate(["Plain", "Regex", "Domain", "Full"]):
        v = et.value.add()
        v.name, v.number = n, i
    f = dom.field.add()
    f.name, f.number = "type", 1
    f.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = dpb.FieldDescriptorProto.TYPE_ENUM
    f.type_name = ".router.Domain.Type"
    f = dom.field.add()
    f.name, f.number = "value", 2
    f.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = dpb.FieldDescriptorProto.TYPE_STRING

    gs = fdp.message_type.add()
    gs.name = "GeoSite"
    f = gs.field.add()
    f.name, f.number = "country_code", 1
    f.label = dpb.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = dpb.FieldDescriptorProto.TYPE_STRING
    f = gs.field.add()
    f.name, f.number = "domain", 2
    f.label = dpb.FieldDescriptorProto.LABEL_REPEATED
    f.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".router.Domain"

    gsl = fdp.message_type.add()
    gsl.name = "GeoSiteList"
    f = gsl.field.add()
    f.name, f.number = "entry", 1
    f.label = dpb.FieldDescriptorProto.LABEL_REPEATED
    f.type = dpb.FieldDescriptorProto.TYPE_MESSAGE
    f.type_name = ".router.GeoSite"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fdp)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("router.GeoSiteList"))


GeoSiteList = _geositelist_cls()

# 单条目类型：(类型名, 域名值)，类型名取自 TYPE_TO_NAME。
Entry = tuple[str, str]


def load(data: bytes) -> dict[str, list[Entry]]:
    lst = GeoSiteList()
    lst.ParseFromString(data)
    return {
        e.country_code: [(TYPE_TO_NAME.get(d.type, str(d.type)), d.value) for d in e.domain]
        for e in lst.entry
    }


def dump(categories: dict[str, list[Entry]]) -> bytes:
    lst = GeoSiteList()
    for code, entries in categories.items():
        site = lst.entry.add()
        site.country_code = code
        for tname, value in entries:
            d = site.domain.add()
            d.type = NAME_TO_TYPE[tname]
            d.value = value
    return lst.SerializeToString()
