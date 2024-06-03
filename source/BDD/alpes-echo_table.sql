-- This script was generated by the ERD tool in pgAdmin 4.
-- Please log an issue at https://redmine.postgresql.org/projects/pgadmin4/issues/new if you find any bugs, including reproduction steps.
BEGIN;

CREATE SEQUENCE IF NOT EXISTS public.api_id_seq;

CREATE SEQUENCE IF NOT EXISTS public.raw_data_id_seq;

CREATE SEQUENCE IF NOT EXISTS public.structured_data_id_seq;

CREATE SEQUENCE IF NOT EXISTS public.webhook_log_id_seq;

CREATE TABLE IF NOT EXISTS public.api
(
    d_creation timestamp(6) with time zone,
    type character varying(100) COLLATE pg_catalog."default",
    name character varying(250) COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    url text COLLATE pg_catalog."default",
    login character varying(250) COLLATE pg_catalog."default",
    password character varying(250) COLLATE pg_catalog."default",
    status integer,
    hkey1 character varying(250) COLLATE pg_catalog."default",
    hkey2 character varying(250) COLLATE pg_catalog."default",
    hkey3 character varying(250) COLLATE pg_catalog."default",
    hkey4 character varying(250) COLLATE pg_catalog."default",
    hvalue1 character varying(250) COLLATE pg_catalog."default",
    hvalue2 character varying(250) COLLATE pg_catalog."default",
    hvalue3 character varying(250) COLLATE pg_catalog."default",
    hvalue4 character varying(250) COLLATE pg_catalog."default",
    id bigint NOT NULL DEFAULT nextval('api_id_seq'::regclass),
    env character varying(250) COLLATE pg_catalog."default" DEFAULT 'test 1'::character varying,
    CONSTRAINT api_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.raw_data
(
    receip_datetime timestamp(6) with time zone,
    json text COLLATE pg_catalog."default",
    endpoint character varying(250) COLLATE pg_catalog."default",
    id bigint NOT NULL DEFAULT nextval('raw_data_id_seq'::regclass),
    CONSTRAINT raw_data_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.structured_data
(
    receip_datetime timestamp(6) with time zone,
    type character varying(250) COLLATE pg_catalog."default",
    date_oem character varying(250) COLLATE pg_catalog."default",
    sn character varying(250) COLLATE pg_catalog."default",
    prod character varying(250) COLLATE pg_catalog."default",
    iccid character varying(250) COLLATE pg_catalog."default",
    imei character varying(250) COLLATE pg_catalog."default",
    lat numeric(1000, 7),
    lng numeric(1000, 7),
    pos_acc numeric(1000, 2),
    mac_address character varying(250) COLLATE pg_catalog."default",
    tag_name character varying(250) COLLATE pg_catalog."default",
    x_acc numeric(1000, 2),
    y_acc numeric(1000, 2),
    z_acc numeric(1000, 2),
    oem_timestamp timestamp(6) with time zone,
    activite numeric(1000, 2),
    endpoint character varying(250) COLLATE pg_catalog."default",
    id bigint NOT NULL DEFAULT nextval('structured_data_id_seq'::regclass),
    alt numeric(1000, 2),
    cap integer,
    pdop numeric(1000, 2),
    volt_bat numeric(1000, 2),
    temperature integer,
    dout numeric(1000, 2),
    peak numeric(1000, 2),
    average numeric(1000, 2),
    duration integer,
    rssi numeric(1000, 2),
    CONSTRAINT oem_data_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.webhook_log
(
    id bigint NOT NULL DEFAULT nextval('webhook_log_id_seq'::regclass),
    id_api bigint,
    url text COLLATE pg_catalog."default",
    method character varying(250) COLLATE pg_catalog."default",
    status character varying(250) COLLATE pg_catalog."default",
    exception text COLLATE pg_catalog."default",
    date timestamp without time zone,
    response text COLLATE pg_catalog."default",
    CONSTRAINT webhook_log_pkey PRIMARY KEY (id)
);
END;