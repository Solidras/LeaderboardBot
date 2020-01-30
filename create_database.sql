CREATE TABLE Server (
id INT PRIMARY KEY);

CREATE TABLE Leaderboard (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
id_server,
to_update INT DEFAULT 0, /*BOOL*/
chan_id INT,
FOREIGN KEY (id_server) REFERENCES Server(id),
UNIQUE(name, id_server));

CREATE TABLE Member (
id INT PRIMARY KEY);

CREATE TABLE Entry (
id INTEGER PRIMARY KEY AUTOINCREMENT,
id_leaderboard INT,
name TEXT,
FOREIGN KEY (id_leaderboard) REFERENCES Leaderboard(id),
UNIQUE(name,id_leaderboard));

CREATE TABLE Vote (
id_member INT,
id_entry INT,
score INT,
FOREIGN KEY (id_member) REFERENCES Member(id),
FOREIGN KEY (id_entry) REFERENCES Entry(id),
PRIMARY KEY (id_member, id_entry));