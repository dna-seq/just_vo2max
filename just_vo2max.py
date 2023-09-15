from oakvar import BasePostAggregator
from pathlib import Path
import sys
cur_path = str(Path(__file__).parent)
sys.path.append(cur_path)
import sqlite3
import vo2max_ref_homo


class CravatPostAggregator (BasePostAggregator):
    sql_insert:str = """ INSERT INTO vo2max (
                        rsid,
                        gene,
                        risk_allele,
                        genotype,
                        conclusion,
                        genotype_conclusion,
                        weight,
                        pmid,
                        population,
                        pvalue,
                        weightcolor
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?) """
    ref_homo:vo2max_ref_homo.Vo2maxRefHomo = vo2max_ref_homo.Vo2maxRefHomo()

    def check(self):
        return True

    def setup (self):
        self.ref_homo.init(self, self.sql_insert)
        modules_path:str = str(Path(__file__).parent)
        sql_file:str = modules_path + "/data/vo2max.sqlite"
        if Path(sql_file).exists():
            self.vo2max_conn:sqlite3.Connection = sqlite3.connect(sql_file)
            self.vo2max_cursor:sqlite3.Cursor = self.vo2max_conn.cursor()

        self.result_path:Path = Path(self.output_dir, self.run_name + "_longevity.sqlite")
        self.longevity_conn:sqlite3.Connection = sqlite3.connect(self.result_path)
        self.longevity_cursor:sqlite3.Cursor = self.longevity_conn.cursor()
        sql_create:str = """ CREATE TABLE IF NOT EXISTS vo2max (
            id integer NOT NULL PRIMARY KEY,
            rsid text,
            gene text,
            risk_allele text,
            genotype text,
            conclusion text,
            genotype_conclusion text,
            weight float,
            pmid text,
            population text,
            pvalue text,
            weightcolor text
            )"""
        self.longevity_cursor.execute(sql_create)
        self.longevity_conn.commit()
        self.longevity_cursor.execute("DELETE FROM vo2max;")
        self.ref_homo.setup()


    def cleanup (self):
        if self.longevity_cursor is not None:
            self.longevity_cursor.close()
        if self.longevity_conn is not None:
            self.longevity_conn.commit()
            self.longevity_conn.close()
        if self.vo2max_cursor is not None:
            self.vo2max_cursor.close()
        if self.vo2max_conn is not None:
            self.vo2max_conn.close()
        return


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


    def annotate (self, input_data:dict):
        rsid:str = str(input_data['dbsnp__rsid'])
        if rsid == '':
            return

        self.ref_homo.process_row(input_data)

        if not rsid.startswith('rs'):
            rsid = "rs" + rsid

        alt:str = input_data['base__alt_base']
        ref:str = input_data['base__ref_base']

        zygot:str = input_data['vcfinfo__zygosity']
        genome:str = alt + ref
        gen_set:set = {alt, ref}
        if zygot == 'hom':
            genome = alt + alt
            gen_set = {alt, alt}

        zygot:str = input_data['vcfinfo__zygosity']
        if zygot is None or zygot == "":
            zygot = "het"

        query_for_rsid:str = f"SELECT gene, risk_allele, rsid_conclusion, pmids, population, p_value FROM rsid WHERE rsid = '{rsid}'"
        self.vo2max_cursor.execute(query_for_rsid)
        rsid_result = self.vo2max_cursor.fetchone()

        query_for_genotype:str = f"SELECT genotype, weight, genotype_specific_conclusion FROM genotype_weights WHERE rsid = '{rsid}' AND allele='{alt}' AND zygot = '{zygot}'"
        self.vo2max_cursor.execute(query_for_genotype)
        genotype = self.vo2max_cursor.fetchone()
    

        if genotype is None or rsid is None:
            return

        row_gen :set= {genotype[0][0], genotype[0][1]}

        task:tuple = (rsid, rsid_result[0], rsid_result[1], genome, rsid_result[2], genotype[2], genotype[1], rsid_result[3], rsid_result[4], rsrsid_resultid[5],
                     self.get_color(((genotype[1]).replace(',','.')), 0.6))

        if gen_set == row_gen:
            self.longevity_cursor.execute(self.sql_insert, task)

        return {"col1":""}


    def postprocess(self):
        self.ref_homo.end()
        pass

