import sqlite3
from sqlite3 import Error


class Vo2maxRefHomo:

    rsid_map:dict = {}

    def init(self, reporter, sql_insert:str):
        self.parent = reporter
        self.sql_insert:str = sql_insert


    def setup(self):
        sql:str = "SELECT rsid, ref_allele, weight, genotype_specific_conclusion FROM genotype_weights WHERE state = 'ref' AND zygosity = 'hom'"
        self.parent.vo2max_cursor.execute(sql)
        rows:list[tuple] = self.parent.vo2max_cursor.fetchall()
        for row in rows:
            self.rsid_map[row[0]] = {'exist':True, 'allele':row[1], 'weight':row[2]}

    def get_color(self, w, scale = 1.5):
        w = float(w.replace(',','.'))
        if w < 0:
            w = w * -1
            w = 1 - w * scale
            if w < 0:
                w = 0
            color = format(int(w * 255), 'x')
            if len(color) == 1:
                color = "0" + color
            color = "ff" + color + color
        else:
            w = 1 - w * scale
            if w < 0:
                w = 0
            color = format(int(w * 255), 'x')
            if len(color) == 1:
                color = "0" + color
            color = color + "ff" + color

        return color

    def process_row(self, row):
        rsid:str = str(row['dbsnp__rsid'])
        if rsid == '':
            return

        if not rsid.startswith('rs'):
            rsid = "rs"+rsid

        item:dict = self.rsid_map.get(rsid)
        if item:
            self.rsid_map[rsid]['exist'] = False


    def end(self):
        for rsid in self.rsid_map:
            if self.rsid_map[rsid]['exist']:
                allele:str = self.rsid_map[rsid]['allele']
                genotype:str = allele+allele

                query_for_rsid = "SELECT gene, risk_allele, rsid_conclusion, pmids, population, p_value FROM rsid WHERE rsid = ?"
                self.parent.vo2max_cursor.execute(query_for_rsid, (rsid,))
                rsid_query = self.parent.vo2max_cursor.fetchone()

                query_for_genotype = "SELECT genotype, weight, genotype_specific_conclusion FROM genotype_weights WHERE rsid = ? AND state='ref' AND zygosity = 'hom'"
                self.parent.vo2max_cursor.execute(query_for_genotype, (rsid,))
                genotype_query = self.parent.vo2max_cursor.fetchone()


                if len(rsid_query) != 0:
                    task:tuple = (rsid, rsid_query[0], rsid_query[1], genotype, rsid_query[2], genotype_query[2], genotype_query[1], rsid_query[3], rsid_query[4], rsid_query[5],
                        self.get_color(((genotype_query[1]).replace(',','.')), 0.6))

                    self.parent.longevity_cursor.execute(self.sql_insert, task)