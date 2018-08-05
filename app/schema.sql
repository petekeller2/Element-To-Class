drop table if exists PageText;
create table PageText (
  id integer primary key autoincrement,
  'text_id' integer not null,
  'language' text not null,
  'text' text not null
);