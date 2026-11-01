from __future__ import annotations
import os, re, json, threading, traceback, webbrowser, shutil, zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

from stemscore_ai.core import load_bundle, prepare_expression, rank_normalize, PLURIPOTENCY_GENES, PROLIFERATION_GENES
from stemscore_ai.input_engine import load_local_expression, fetch_geo_expression
from stemscore_ai.engine import classify_expression
from stemscore_ai.lineage import LINEAGE_PANELS, score_all_lineages
from stemscore_ai.microscopy import IMAGE_EXTS, analyze_paths
from stemscore_ai import publication as pub

APP_VERSION='StemScore AI v7.1 | Frozen Core | Lineage + Trajectory + QC + Microscopy | Publication Export'
BASE=Path(__file__).resolve().parent
MODEL=BASE/'stemscore_core.joblib'
OUT=Path.home()/'StemScoreAI_Results'; OUT.mkdir(exist_ok=True)
# Journal-standard look (Okabe-Ito colour-blind-safe palette, Arial/Helvetica, editable-text vector output)
matplotlib.rcParams.update(pub.journal_rc())

class App:
    def __init__(self,root):
        self.root=root; root.title('StemScore AI v7.1 — Human Stem-Cell Gene-Expression Analyzer'); root.geometry('1450x850'); root.minsize(1200,700)
        self.bundle=load_bundle(MODEL); self.current=None; self.expr=None; self.meta=None; self.prediction_model=self.bundle.model; self.prediction_genes=list(self.bundle.model_genes); self.source=''; self.busy=False; self.gene_contrib=None; self.marker_analysis=None; self.lineage_scores=None; self.lineage_ranks=None; self.lineage_marker_genes=[]
        self._style(); self._ui()
    def clear_all_results(self):
        """Clear current in-memory analysis and visible results, without deleting saved files or the frozen model."""
        if not messagebox.askyesno('Clear all results', 'Clear all current analysis results, validation labels, graphs, tables, and selected microscopy images?\n\nSaved files on disk and the frozen model will not be deleted.'):
            return
        self.current=None; self.expr=None; self.meta=None; self.source=''; self.gene_contrib=None; self.marker_analysis=None
        self.lineage_scores=None; self.lineage_ranks=None; self.lineage_marker_genes=[]
        self.expected_lineage=None; self.validation_results=None; self.micro_paths=[]; self.micro_results=None
        self.prediction_model=self.bundle.model; self.prediction_genes=list(self.bundle.model_genes)
        # Clear expression result table and summaries.
        for tree in (self.tree, self.contrib_tree, self.marker_tree, self.state_tree, self.micro_tree):
            for item in tree.get_children(): tree.delete(item)
        self.summary.configure(text='No analysis yet.')
        self.cover.configure(text='')
        self.contrib_combo['values']=(); self.contrib_sample.set('')
        self.contrib_status.configure(text='Run a GEO or local expression analysis first.')
        self.lineage_status.configure(text='Run an analysis first. For formal validation, load independent expected labels and click Run Validation.')
        self.lineage_validation_metrics.configure(text='No independent labels loaded.')
        self.gstatus.delete('1.0','end'); self.gstatus.insert('end','No GEO analysis results currently displayed. Enter an accession and fetch when ready.\n')
        self.linfo.delete('1.0','end'); self.linfo.insert('end','No file loaded. Browse to select a new gene-expression matrix.\n')
        self.path.set(''); self.gse.set('')
        # Reset all plot panels to explicit empty states.
        self.lineage_ax.clear(); self.lineage_ax.set_axis_off(); self.lineage_ax.text(.5,.5,'Run an analysis first.',ha='center',va='center',transform=self.lineage_ax.transAxes); self.lineage_canvas.draw_idle()
        self.heat_ax.clear(); self.heat_ax.set_axis_off(); self.heat_ax.text(.5,.5,'Run an analysis first.',ha='center',va='center',transform=self.heat_ax.transAxes); self.heat_canvas.draw_idle()
        self.state_ax.clear(); self.state_ax.set_axis_off(); self.state_ax.text(.5,.5,'Run an analysis first.',ha='center',va='center',transform=self.state_ax.transAxes); self.state_canvas.draw_idle()
        self._draw_validation_empty()
        self.micro_clear()
        self.status.set('Cleared current results. Ready for new samples; saved exports and the frozen model were preserved.')

    def _style(self):
        s=ttk.Style();
        try:s.theme_use('clam')
        except:pass
        s.configure('Title.TLabel',font=('Segoe UI',20,'bold')); s.configure('Sub.TLabel',font=('Segoe UI',10)); s.configure('Big.TButton',font=('Segoe UI',12,'bold'),padding=10)
    def _ui(self):
        top=ttk.Frame(self.root,padding=14); top.pack(fill='x')
        ttk.Label(top,text='StemScore AI',style='Title.TLabel').pack(anchor='w')
        ttk.Label(top,text='GEO-integrated human stem-cell gene-expression analysis | '+APP_VERSION,style='Sub.TLabel').pack(anchor='w')
        nb=ttk.Notebook(self.root); nb.pack(fill='both',expand=True,padx=12,pady=8)
        self.geo=ttk.Frame(nb,padding=14); self.local=ttk.Frame(nb,padding=14); self.results=ttk.Frame(nb,padding=14); self.contrib=ttk.Frame(nb,padding=14); self.lineage=ttk.Frame(nb,padding=14); self.micro=ttk.Frame(nb,padding=14)
        nb.add(self.geo,text='GEO Analysis'); nb.add(self.local,text='Gene Expression File'); nb.add(self.results,text='Results'); nb.add(self.contrib,text='Gene Contribution'); nb.add(self.lineage,text='Lineage Analysis'); nb.add(self.micro,text='Microscopy AI')
        self._geo_ui(); self._local_ui(); self._results_ui(); self._contrib_ui(); self._lineage_ui(); self._micro_ui()
        self.status=tk.StringVar(value='Ready — enter a GEO accession or load a gene-expression file.')
        footer=ttk.Frame(self.root,padding=(6,3))
        footer.pack(fill='x',side='bottom')
        ttk.Label(footer,textvariable=self.status,relief='sunken',anchor='w').pack(side='left',fill='x',expand=True)
        ttk.Button(footer,text='Clear All Results / New Samples',command=self.clear_all_results).pack(side='right',padx=(8,0))
    def _geo_ui(self):
        f=self.geo; ttk.Label(f,text='GEO accession',font=('Segoe UI',13,'bold')).pack(anchor='w')
        row=ttk.Frame(f); row.pack(fill='x',pady=8)
        self.gse=tk.StringVar(value='GSE70741'); ttk.Entry(row,textvariable=self.gse,font=('Consolas',13),width=24).pack(side='left')
        self.gbtn=ttk.Button(row,text='FETCH GEO + ANALYZE',style='Big.TButton',command=self.fetch); self.gbtn.pack(side='left',padx=12)
        self.gstatus=tk.Text(f,height=20,wrap='word'); self.gstatus.pack(fill='both',expand=True,pady=10)
        self.gstatus.insert('end','Enter any GEO Series accession (for example GSE70741).\n\nThe app retrieves GEO metadata and processed expression data when available, standardizes identifiers, checks coverage, and runs StemScore.\n\nRaw FASTQ/RAW archives are not silently treated as expression matrices; if a study only provides raw data, the app will tell you that preprocessing is required.\n')
    def _local_ui(self):
        f=self.local; ttk.Label(f,text='Gene-expression file',font=('Segoe UI',13,'bold')).pack(anchor='w')
        ttk.Label(f,text='Supported: CSV, TSV/TXT, XLSX/XLS, compressed expression tables. The loader detects headers and gene-ID style automatically.',wraplength=1000).pack(anchor='w',pady=6)
        self.path=tk.StringVar(); row=ttk.Frame(f); row.pack(fill='x',pady=8)
        ttk.Entry(row,textvariable=self.path).pack(side='left',fill='x',expand=True); ttk.Button(row,text='Browse',command=self.browse).pack(side='left',padx=6)
        ttk.Button(f,text='RUN STEMSCORE',style='Big.TButton',command=self.local_run).pack(anchor='w',pady=10)
        self.linfo=tk.Text(f,height=20,wrap='word'); self.linfo.pack(fill='both',expand=True); self.linfo.insert('end','No file loaded.\n')
    def _results_ui(self):
        f=self.results
        self.summary=ttk.Label(f,text='No analysis yet.',font=('Segoe UI',14,'bold')); self.summary.pack(anchor='w')
        self.cover=ttk.Label(f,text=''); self.cover.pack(anchor='w',pady=5)
        cols=('Sample','State','P(Pluri)','P(Progenitor)','P(Diff)','Confidence','Pluripotency','Proliferation','Model coverage')
        tf=ttk.Frame(f); tf.pack(fill='both',expand=True,pady=8)
        self.tree=ttk.Treeview(tf,columns=cols,show='headings'); vs=ttk.Scrollbar(tf,orient='vertical',command=self.tree.yview); hs=ttk.Scrollbar(tf,orient='horizontal',command=self.tree.xview); self.tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        for c in cols:self.tree.heading(c,text=c); self.tree.column(c,width=125,anchor='center')
        self.tree.grid(row=0,column=0,sticky='nsew'); vs.grid(row=0,column=1,sticky='ns'); hs.grid(row=1,column=0,sticky='ew'); tf.rowconfigure(0,weight=1); tf.columnconfigure(0,weight=1)
        bf=ttk.Frame(f); bf.pack(fill='x'); ttk.Button(bf,text='Save CSV',command=self.save_csv).pack(side='left'); ttk.Button(bf,text='Create PDF Report',command=self.pdf).pack(side='left',padx=8); ttk.Button(bf,text='Open Results Folder',command=lambda:os.startfile(OUT) if os.name=='nt' else webbrowser.open(OUT.as_uri())).pack(side='left')
    def _setbusy(self,b):
        self.busy=b; self.gbtn.configure(state='disabled' if b else 'normal');
        self.status.set('Working… please wait; the interface remains responsive.' if b else 'Ready.')
    def browse(self):
        p=filedialog.askopenfilename(filetypes=[('Expression files','*.csv *.tsv *.txt *.xlsx *.xls *.gz'),('All files','*.*')]);
        if p:self.path.set(p)
    def fetch(self):
        if self.busy:return
        acc=self.gse.get().strip().upper(); self._setbusy(True); self.gstatus.delete('1.0','end'); self.gstatus.insert('end',f'Connecting to NCBI GEO: {acc}\n')
        threading.Thread(target=self._fetch_worker,args=(acc,),daemon=True).start()
    def _fetch_worker(self,acc):
        try:
            def prog(done,total):
                if total: self.root.after(0,lambda:self.status.set(f'Downloading GEO expression data: {done/total*100:.1f}%'))
                else:self.root.after(0,lambda:self.status.set(f'Downloading GEO expression data: {done/1024/1024:.1f} MB'))
            expr,meta=fetch_geo_expression(acc,progress=prog,workdir=OUT/'geo_cache'/acc,reference_genes=self.bundle.rank_universe); self.root.after(0,lambda:self._finish(expr,meta,f'GEO:{acc}'))
        except Exception as e:self._report_worker_error(e)
    def local_run(self):
        p=self.path.get().strip()
        if not p:return messagebox.showwarning('Input','Select a gene-expression file first.')
        if self.busy:return
        self._setbusy(True); threading.Thread(target=self._local_worker,args=(p,),daemon=True).start()
    def _local_worker(self,p):
        try:
            self.root.after(0,lambda:self.status.set('Reading expression file and detecting gene IDs…'))
            expr=load_local_expression(p,reference_genes=self.bundle.rank_universe); meta={'source_type':'Local file','source_url':p,'accession':'LOCAL'}
            self.root.after(0,lambda:self._finish(expr,meta,p))
        except Exception as e:self._report_worker_error(e)
    def _finish(self,expr,meta,source):
        try:
            self.root.after(0,lambda:self.status.set(f'Running StemScore on {expr.shape[0]:,} genes × {expr.shape[1]:,} samples…'))
            result,ameta=classify_expression(self.bundle,expr)
            self.prediction_model=result.attrs.pop('_prediction_model',self.bundle.model)
            self.prediction_genes=result.attrs.pop('_prediction_genes',list(self.bundle.model_genes))
            # Validation labels/results belong to a specific expression dataset; never carry them silently to a new dataset.
            self.expected_lineage=None; self.validation_results=None
            meta.update(ameta); self.current=result; self.expr=expr.copy(); self.meta=meta; self.source=source
            self._populate(result,meta,expr)
            self._refresh_contribution()
            self._refresh_lineage()
            self.lineage_validation_metrics.configure(text='No independent labels loaded for this dataset.')
            self._draw_validation_empty()
            self._setbusy(False)
        except Exception as e:self._report_worker_error(e)
    def _report_worker_error(self,e):
        """Safe from worker threads: copies the message NOW (Python deletes `e` when the except block ends), logs the traceback, hints at network causes."""
        msg=f'{type(e).__name__}: {e}'; tb=traceback.format_exc()
        try:
            with open(OUT/'StemScoreAI_crash_log.txt','a',encoding='utf-8') as f: f.write(f"\n[handled error {datetime.now().isoformat(timespec='seconds')}]\n{tb}")
        except Exception: pass
        low=msg.lower()
        if any(k in low for k in ('ssl','certificate','connection','timed out','timeout','max retries','getaddrinfo','name resolution','proxy','403','404')):
            msg+='\n\nThis looks like a network or access problem. Check: internet connection; VPN/proxy/firewall/antivirus allowing ncbi.nlm.nih.gov and ftp.ncbi.nlm.nih.gov; that the GSE number exists and has a Series Matrix file. You can also download the matrix manually from the GEO page and use the \'Gene Expression File\' tab.'
        self.root.after(0,lambda m=msg:self._error(m))
    def _error(self,msg):
        self._setbusy(False); self.status.set('Analysis stopped — see error details.'); messagebox.showerror('StemScore analysis',msg)
    def _populate(self,res,meta,expr):
        for x in self.tree.get_children():self.tree.delete(x)
        for idx,row in res.iterrows():
            self.tree.insert('', 'end', values=(str(idx),str(row.get('Predicted_State','')),f"{float(row.get('Pluripotent',np.nan)):.3f}",f"{float(row.get('Progenitor',np.nan)):.3f}",f"{float(row.get('Differentiated',np.nan)):.3f}",f"{float(row.get('Confidence',np.nan)):.3f}",f"{float(row.get('Pluripotency_Score',np.nan)):.3f}",f"{float(row.get('Proliferation_Score',np.nan)):.3f}" if pd.notna(row.get('Proliferation_Score',np.nan)) else '—',f"{float(row.get('Model_Gene_Coverage',meta.get('model_gene_coverage',np.nan)))*100:.1f}%"))
        states=res['Predicted_State'].value_counts().to_dict(); main=res['Predicted_State'].mode().iat[0] if len(res) else 'Unknown'
        self.summary.configure(text=f'Most frequent predicted state: {main}')
        self.cover.configure(text=f"Samples: {len(res)} | Genes: {expr.shape[0]:,} | Mode: {meta.get('analysis_mode','')} | Rank coverage: {meta.get('rank_universe_coverage',0)*100:.1f}% | Model coverage: {meta.get('model_gene_coverage',0)*100:.1f}% | States: {states}")
        self.results.event_generate('<<ResultReady>>')
        self._draw_state_probability()
        self.status.set('Analysis complete.')
        self.root.after(0,lambda:self.gstatus.insert('end',f'\nCompleted: {expr.shape[0]:,} genes × {expr.shape[1]:,} samples.\nAnalysis mode: {meta.get("analysis_mode")}\n'))
        self.root.after(0,lambda:self.linfo.insert('end',f'\nLoaded: {expr.shape[0]:,} genes × {expr.shape[1]:,} samples\nAnalysis mode: {meta.get("analysis_mode")}\n'))

    def _lineage_ui(self):
        f=self.lineage
        ttk.Label(f,text='Lineage Scoring / Independent Validation',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(f,text='Lineage scores are descriptive until independent expected-lineage labels are supplied. Validation never retrains the frozen model.',wraplength=1200).pack(anchor='w',pady=4)
        bar=ttk.Frame(f); bar.pack(fill='x',pady=6)
        ttk.Button(bar,text='Refresh Lineage Analysis',style='Big.TButton',command=self._refresh_lineage).pack(side='left')
        ttk.Button(bar,text='Load Expected Lineage CSV',command=self._load_expected_lineage).pack(side='left',padx=8)
        ttk.Button(bar,text='Run Validation',style='Big.TButton',command=self._run_lineage_validation).pack(side='left',padx=8)
        ttk.Button(bar,text='Create Validation Template',command=self._create_lineage_template).pack(side='left',padx=8)
        ttk.Button(bar,text='Export Validation',command=self._export_lineage_validation).pack(side='left',padx=8)
        ttk.Button(bar,text='Save Validation Figures',command=self._save_validation_graphs).pack(side='left',padx=8)
        ttk.Button(bar,text='Save State Trajectory Figure',command=self._save_state_probability).pack(side='left',padx=8)
        # Keep graph-export controls on their own row so neither is clipped
        # when the desktop window is narrower than the full toolbar width.
        export_bar=ttk.Frame(f)
        export_bar.pack(fill='x',pady=(0,6))
        ttk.Button(export_bar,text='Export Lineage Trajectory (PDF/SVG/TIFF/PNG)',command=self._save_lineage_trajectory).pack(side='left',padx=(0,8))
        ttk.Button(export_bar,text='Export Lineage Heatmap (PDF/SVG/TIFF/PNG)',command=self._save_lineage_heatmap).pack(side='left',padx=(0,8))
        ttk.Button(export_bar,text='EXPORT PUBLICATION PACK (Figures + Tables + Methods)',style='Big.TButton',command=self._export_publication_pack).pack(side='left',padx=(8,8))
        self.lineage_status=ttk.Label(f,text='Run an analysis first. For formal validation, load a CSV with Sample and Expected_Lineage columns.')
        self.lineage_status.pack(anchor='w',pady=4)

        # Scrollable 2x2 grid: every graph has its own column and row.
        outer=ttk.Frame(f); outer.pack(fill='both',expand=True)
        canvas=tk.Canvas(outer,highlightthickness=0)
        vs=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        canvas.grid(row=0,column=0,sticky='nsew'); vs.grid(row=0,column=1,sticky='ns')
        outer.rowconfigure(0,weight=1); outer.columnconfigure(0,weight=1)
        content=ttk.Frame(canvas,padding=(2,2,10,10))
        win=canvas.create_window((0,0),window=content,anchor='nw')
        def _sync(_event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfigure(win,width=max(canvas.winfo_width()-4,900))
        content.bind('<Configure>',_sync); canvas.bind('<Configure>',_sync)
        self._lineage_scroll_canvas=canvas

        for c in (0,1): content.columnconfigure(c,weight=1,uniform='graphs')
        content.rowconfigure(0,weight=1); content.rowconfigure(1,weight=1)

        # Row 0: descriptive lineage graphs in separate columns.
        graph_pane=ttk.Frame(content,padding=(0,2,8,8)); graph_pane.grid(row=0,column=0,sticky='nsew')
        heat_pane=ttk.Frame(content,padding=(8,2,0,8)); heat_pane.grid(row=0,column=1,sticky='nsew')
        ttk.Label(graph_pane,text='Lineage-score trajectory',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.lineage_fig=plt.Figure(figsize=(pub.COL_1_5,3.2),dpi=150); self.lineage_ax=self.lineage_fig.add_subplot(111)
        self.lineage_canvas=FigureCanvasTkAgg(self.lineage_fig,master=graph_pane); self.lineage_canvas.get_tk_widget().pack(fill='both',expand=True)
        ttk.Label(heat_pane,text='Lineage marker heatmap',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.heat_fig=plt.Figure(figsize=(pub.COL_1_5,4.8),dpi=150); self.heat_ax=self.heat_fig.add_subplot(111)
        self.heat_canvas=FigureCanvasTkAgg(self.heat_fig,master=heat_pane); self.heat_canvas.get_tk_widget().pack(fill='both',expand=True)

        # Row 1: cell-state probability trajectory (the GSE70741-style graph), kept
        # separate from lineage scoring. This is generated from the loaded dataset,
        # never hard-coded to GSE70741.
        state_pane=ttk.Frame(content,padding=(0,2,8,8)); state_pane.grid(row=1,column=0,sticky='nsew')
        state_info=ttk.Frame(content,padding=(8,2,0,8)); state_info.grid(row=1,column=1,sticky='nsew')
        ttk.Label(state_pane,text='Cell-state probability trajectory',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.state_fig=plt.Figure(figsize=(pub.COL_1_5,3.2),dpi=150); self.state_ax=self.state_fig.add_subplot(111)
        self.state_canvas=FigureCanvasTkAgg(self.state_fig,master=state_pane); self.state_canvas.get_tk_widget().pack(fill='both',expand=True)
        ttk.Label(state_info,text='Loaded sample predictions',font=('Segoe UI',11,'bold')).pack(anchor='w')
        stf=ttk.Frame(state_info); stf.pack(fill='both',expand=True,pady=2)
        state_cols=('Sample','Prediction','P(Pluripotent)','P(Progenitor)','P(Differentiated)','Confidence')
        self.state_tree=ttk.Treeview(stf,columns=state_cols,show='headings')
        sv=ttk.Scrollbar(stf,orient='vertical',command=self.state_tree.yview); sh=ttk.Scrollbar(stf,orient='horizontal',command=self.state_tree.xview)
        self.state_tree.configure(yscrollcommand=sv.set,xscrollcommand=sh.set)
        for c in state_cols:
            self.state_tree.heading(c,text=c); self.state_tree.column(c,width=120,anchor='center')
        self.state_tree.grid(row=0,column=0,sticky='nsew'); sv.grid(row=0,column=1,sticky='ns'); sh.grid(row=1,column=0,sticky='ew'); stf.rowconfigure(0,weight=1); stf.columnconfigure(0,weight=1)

        # Row 2: formal independent validation graphs in separate columns.
        val_head=ttk.Frame(content); val_head.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(4,2))
        ttk.Label(val_head,text='Independent Lineage Validation',font=('Segoe UI',13,'bold')).pack(anchor='w')
        metrics=ttk.Frame(val_head); metrics.pack(fill='x',pady=2)
        self.lineage_validation_metrics=ttk.Label(metrics,text='No independent labels loaded.',font=('Segoe UI',10))
        self.lineage_validation_metrics.pack(anchor='w')
        cm_pane=ttk.Frame(content,padding=(0,2,8,8)); cm_pane.grid(row=3,column=0,sticky='nsew')
        sep_pane=ttk.Frame(content,padding=(8,2,0,8)); sep_pane.grid(row=3,column=1,sticky='nsew')
        content.rowconfigure(3,weight=1)
        ttk.Label(cm_pane,text='Expected vs Predicted — Confusion Matrix',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.cm_fig=plt.Figure(figsize=(pub.COL_1_5,3.2),dpi=150); self.cm_ax=self.cm_fig.add_subplot(111)
        self.cm_canvas=FigureCanvasTkAgg(self.cm_fig,master=cm_pane); self.cm_canvas.get_tk_widget().pack(fill='both',expand=True)
        ttk.Label(sep_pane,text='Lineage-score separation by sample',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.sep_fig=plt.Figure(figsize=(pub.COL_1_5,3.2),dpi=150); self.sep_ax=self.sep_fig.add_subplot(111)
        self.sep_canvas=FigureCanvasTkAgg(self.sep_fig,master=sep_pane); self.sep_canvas.get_tk_widget().pack(fill='both',expand=True)
        self.expected_lineage=None
        self.validation_results=None
        self.cm_colorbar=None
        self._draw_validation_empty()

    def _reset_axes(self,fig,attr):
        fig.clf(); ax=fig.add_subplot(111); setattr(self,attr,ax); return ax

    def _empty_panel(self,fig,attr,canvas,msg):
        ax=self._reset_axes(fig,attr); ax.set_axis_off()
        ax.text(.5,.5,msg,ha='center',va='center',fontsize=9,color=pub.OI['grey']); canvas.draw()

    def _draw_validation_empty(self):
        self.cm_colorbar=None
        self._empty_panel(self.cm_fig,'cm_ax',self.cm_canvas,'Load expected lineage labels\nto generate validation.')
        self._empty_panel(self.sep_fig,'sep_ax',self.sep_canvas,'Independent validation graph\nwill appear here.')
        self._draw_state_probability()

    def _create_lineage_template(self):
        if self.lineage_scores is None or self.lineage_scores.empty:
            return messagebox.showwarning('Validation template','Run a GEO or local expression analysis first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='Expected_Lineage_TEMPLATE.csv',defaultextension='.csv',filetypes=[('CSV','*.csv')],title='Save expected lineage template')
        if not p:return
        try:
            pd.DataFrame({'Sample':[str(x) for x in self.lineage_scores.index],'Expected_Lineage':['']*len(self.lineage_scores)}).to_csv(p,index=False)
            messagebox.showinfo('Template created',f'Fill the Expected_Lineage column with Neural, Cardiac, or Hepatic labels, then load the CSV.\n\nSaved to:\n{p}')
        except Exception as e: messagebox.showerror('Template failed',f'{type(e).__name__}: {e}')

    def _load_expected_lineage(self):
        p=filedialog.askopenfilename(initialdir=OUT,filetypes=[('CSV','*.csv'),('Excel workbook','*.xlsx')],title='Select expected lineage labels')
        if not p:return
        try:
            df=pd.read_csv(p) if p.lower().endswith('.csv') else pd.read_excel(p)
            cols={str(c).strip().lower():c for c in df.columns}
            sample_col=cols.get('sample') or cols.get('sample_name') or cols.get('sample id')
            label_col=cols.get('expected_lineage') or cols.get('expected lineage') or cols.get('lineage') or cols.get('true_lineage')
            if sample_col is None or label_col is None:
                raise ValueError('File must contain Sample and Expected_Lineage columns.')
            x=df[[sample_col,label_col]].copy(); x.columns=['Sample','Expected_Lineage']
            x['Sample']=x['Sample'].astype(str).str.strip()
            x['Expected_Lineage']=x['Expected_Lineage'].fillna('').astype(str).str.strip().str.title()
            x=x[(x['Sample']!='') & (x['Expected_Lineage']!='')]
            if x.empty:
                raise ValueError('No expected labels were supplied. Fill Expected_Lineage with independently verified labels before loading.')
            if x['Sample'].duplicated().any():
                dup=sorted(x.loc[x['Sample'].duplicated(keep=False),'Sample'].unique())
                raise ValueError('Duplicate sample IDs found: '+', '.join(dup))
            allowed=set(LINEAGE_PANELS)
            bad=sorted(set(x.Expected_Lineage)-allowed)
            if bad:
                raise ValueError('Unsupported lineage labels: '+', '.join(bad)+'. Use Neural, Cardiac, or Hepatic.')
            self.expected_lineage=x.set_index('Sample')['Expected_Lineage']
            self.validation_results=None
            self.lineage_validation_metrics.configure(text=f'Loaded {len(x)} expected labels from {Path(p).name}. Click Run Validation to compare with the current predictions.')
            self._draw_validation_empty()
            messagebox.showinfo('Validation labels loaded',f'Loaded {len(x)} non-empty expected labels.\n\nNext: click Run Validation.\nLabels must be independent of StemScore predictions.')
        except Exception as e:
            messagebox.showerror('Validation labels',f'{type(e).__name__}: {e}')

    def _run_lineage_validation(self):
        if self.lineage_scores is None or self.lineage_scores.empty:
            return messagebox.showwarning('Validation','Run a GEO or local expression analysis first.')
        if self.expected_lineage is None or self.expected_lineage.empty:
            return messagebox.showwarning('Validation','Click Load Expected Lineage CSV and select a completed file first.')
        self._refresh_lineage_validation()

    def _refresh_lineage_validation(self):
        if self.lineage_scores is None or self.lineage_scores.empty or self.expected_lineage is None:
            return
        common=[str(s) for s in self.lineage_scores.index if str(s) in self.expected_lineage.index]
        if not common:
            self.validation_results=None
            self.lineage_validation_metrics.configure(text='No matching sample names. Check that Sample IDs exactly match the expression dataset.')
            self._draw_validation_empty()
            return
        y_true=self.expected_lineage.loc[common].astype(str)
        y_pred=self.lineage_scores.loc[common,'Top_Lineage'].astype(str)
        acc=accuracy_score(y_true,y_pred)
        bal=balanced_accuracy_score(y_true,y_pred)
        f1=f1_score(y_true,y_pred,labels=list(LINEAGE_PANELS),average='macro',zero_division=0)
        pre=precision_score(y_true,y_pred,labels=list(LINEAGE_PANELS),average='macro',zero_division=0)
        rec=recall_score(y_true,y_pred,labels=list(LINEAGE_PANELS),average='macro',zero_division=0)
        margins=[]
        for sample in common:
            vals=sorted([float(self.lineage_scores.loc[sample,c]) for c in LINEAGE_PANELS],reverse=True)
            margins.append(vals[0]-vals[1])
        self.validation_results=pd.DataFrame({'Sample':common,'Expected_Lineage':y_true.values,'Predicted_Lineage':y_pred.values,'Lineage_Margin':margins})
        unmatched=sorted(set(self.expected_lineage.index.astype(str))-set(common))
        note=f' | Unmatched expected IDs: {len(unmatched)}' if unmatched else ''
        self.lineage_validation_metrics.configure(text=f'N={len(common)} matched | Accuracy={acc:.3f} | Balanced accuracy={bal:.3f} | Macro-F1={f1:.3f} | Macro-precision={pre:.3f} | Macro-recall={rec:.3f} | Mean margin={np.mean(margins):.3f}{note}')
        self._draw_confusion(y_true,y_pred)
        self._draw_separation(common)
        if unmatched:
            messagebox.showwarning('Validation completed with unmatched IDs',f'Validation used {len(common)} matched samples. {len(unmatched)} expected-label sample IDs did not match the loaded expression data. Check sample names before interpreting the metrics.')
        else:
            messagebox.showinfo('Validation complete',f'Validation completed for {len(common)} matched samples.\n\nUse these metrics cautiously: the labels must be independent, and a small sample count does not establish broad generalization.')

    def _draw_confusion(self,y_true,y_pred):
        self.cm_colorbar=None
        ax=self._reset_axes(self.cm_fig,'cm_ax')
        pub.draw_confusion(self.cm_fig,ax,list(y_true),list(y_pred),list(LINEAGE_PANELS))
        self.cm_fig.tight_layout(); self.cm_canvas.draw()

    def _draw_separation(self,common):
        ax=self._reset_axes(self.sep_fig,'sep_ax')
        pub.draw_separation(ax,self.lineage_scores,list(common),LINEAGE_PANELS)
        self.sep_fig.tight_layout(); self.sep_canvas.draw()

    def _export_lineage_validation(self):
        if self.validation_results is None:return messagebox.showwarning('Validation','Load expected lineage labels and run validation first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Lineage_Validation.xlsx',defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx'),('CSV','*.csv')])
        if not p:return
        try:
            if p.lower().endswith('.csv'): self.validation_results.to_csv(p,index=False)
            else:
                with pd.ExcelWriter(p,engine='openpyxl') as w:
                    self.validation_results.to_excel(w,index=False,sheet_name='Sample_Validation')
                    self.lineage_scores.to_excel(w,sheet_name='Lineage_Scores')
                    if self.lineage_ranks is not None:self.lineage_ranks.to_excel(w,sheet_name='Marker_Ranks')
            messagebox.showinfo('Validation export',f'Validation results saved to:\n{p}')
        except Exception as e: messagebox.showerror('Export failed',f'{type(e).__name__}: {e}')

    def _validation_tuple(self):
        vr=self.validation_results
        if vr is None or vr.empty: return None
        return (list(vr['Expected_Lineage']),list(vr['Predicted_Lineage']),list(LINEAGE_PANELS))

    def _save_multi(self,fig,stem,title):
        """Save ONE figure as PDF + SVG (vector, editable text) and TIFF + PNG (600 dpi)."""
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile=stem,defaultextension='.pdf',filetypes=[('Publication figure (saves PDF + SVG + TIFF 600 dpi + PNG 600 dpi)','*.pdf')],title=title)
        if not p:return
        try:
            files=pub.save_figure_all(fig,p)
            messagebox.showinfo('Figure saved','Saved:\n'+'\n'.join(f.name for f in files)+f'\n\nFolder:\n{Path(p).parent}')
        except Exception as e: messagebox.showerror('Save failed',f'{type(e).__name__}: {e}')

    def _save_validation_graphs(self):
        v=self._validation_tuple()
        if v is None:return messagebox.showwarning('Validation','Run independent validation first.')
        folder=filedialog.askdirectory(initialdir=OUT,title='Select validation output folder')
        if not folder:return
        try:
            common=list(self.validation_results['Sample'])
            a=pub.save_figure_all(pub.fig_confusion(*v),Path(folder)/'StemScore_Lineage_Confusion_Matrix')
            b=pub.save_figure_all(pub.fig_separation(self.lineage_scores,common,LINEAGE_PANELS),Path(folder)/'StemScore_Lineage_Score_Separation')
            messagebox.showinfo('Saved',f'Validation graphs saved ({len(a)+len(b)} files: PDF, SVG, TIFF, PNG).')
        except Exception as e: messagebox.showerror('Save failed',f'{type(e).__name__}: {e}')

    def _export_publication_pack(self):
        if self.current is None or self.current.empty or self.lineage_scores is None or self.lineage_ranks is None or self.lineage_ranks.empty:
            return messagebox.showwarning('Publication pack','Run a GEO or local expression analysis first.')
        folder=filedialog.askdirectory(initialdir=OUT,title='Select a folder for the publication pack')
        if not folder:return
        sub=Path(folder)/('StemScore_Publication_Pack_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        try:
            self.root.configure(cursor='watch'); self.root.update_idletasks()
            files=pub.export_publication_pack(sub,self.current,self.lineage_scores,self.lineage_ranks,LINEAGE_PANELS,self.meta,MODEL,APP_VERSION,validation=self._validation_tuple(),validation_df=self.validation_results,expr_shape=self.expr.shape if self.expr is not None else None)
            self.root.configure(cursor='')
            messagebox.showinfo('Publication pack created',f'{len(files)} files written to:\n{sub}\n\nIncludes Figure 1 + individual panels (PDF, SVG, TIFF 600 dpi, PNG 600 dpi), supplementary tables (CSV + XLSX), Methods.txt, Figure_legends.txt and provenance.json.')
            try: os.startfile(str(sub))
            except Exception: pass
        except Exception as e:
            self.root.configure(cursor=''); messagebox.showerror('Publication pack failed',f'{type(e).__name__}: {e}')

    def _sample_order(self, samples):
        def key(s):
            m=re.search(r'(?i)(?:day|d)[ _-]?(\d+(?:\.\d+)?)',str(s))
            if m:
                return (0,float(m.group(1)),str(s))
            return (1,0,str(s))
        return sorted([str(x) for x in samples],key=key)

    def _refresh_lineage(self):
        if self.expr is None:
            self.lineage_status.configure(text='Run a GEO or local expression analysis first.')
            return
        try:
            scores,cov=score_all_lineages(self.expr)
            self.lineage_scores=scores.copy()
            order=self._sample_order(scores.index)
            self.lineage_scores=self.lineage_scores.loc[order]
            shared=[g for p in LINEAGE_PANELS.values() for g in p if g in self.expr.index]
            # Preserve marker order and remove duplicates.
            genes=[]
            for p in LINEAGE_PANELS.values():
                for g in p:
                    if g in self.expr.index and g not in genes: genes.append(g)
            self.lineage_marker_genes=genes
            if genes:
                self.lineage_ranks=self.expr.loc[genes,order].rank(axis=0,pct=True)
            else:
                self.lineage_ranks=pd.DataFrame(index=[],columns=order)
            self._draw_lineage_trajectory()
            self._draw_lineage_heatmap()
            tops=self.lineage_scores['Top_Lineage'].value_counts().to_dict()
            coverage=' | '.join(f'{k}: {float(cov.loc["Marker_Coverage",k])*100:.1f}%' for k in LINEAGE_PANELS)
            self.lineage_status.configure(text=f'Samples: {len(order)} | Top lineage counts: {tops} | Marker coverage — {coverage}')
            if self.expected_lineage is not None:
                self.lineage_validation_metrics.configure(text='Expected labels are loaded. Click Run Validation to evaluate this dataset.')
        except Exception as e:
            self.lineage_status.configure(text=f'Lineage analysis unavailable: {type(e).__name__}: {e}')

    def _draw_state_probability(self):
        for item in self.state_tree.get_children(): self.state_tree.delete(item)
        if self.current is None or self.current.empty:
            self._empty_panel(self.state_fig,'state_ax',self.state_canvas,'Run a GEO or local expression analysis first.')
            return
        ax=self._reset_axes(self.state_fig,'state_ax')
        pub.draw_state_trajectory(ax,self.current)
        self.state_fig.tight_layout(); self.state_canvas.draw()
        order=[str(x) for x in self.current.index]
        if all(pub.parse_day(n) is not None for n in order):
            order=sorted(order,key=lambda n:(pub.parse_day(n),n))
        cur=self.current.copy(); cur.index=[str(x) for x in cur.index]
        for name in order:
            r=cur.loc[name]
            if isinstance(r,pd.DataFrame): r=r.iloc[0]
            self.state_tree.insert('', 'end', values=(name,str(r['Predicted_State']),f"{float(r['Pluripotent']):.3f}",f"{float(r['Progenitor']):.3f}",f"{float(r['Differentiated']):.3f}",f"{float(r['Confidence']):.3f}"))

    def _draw_lineage_trajectory(self):
        if self.lineage_scores is None or self.lineage_scores.empty:
            self._empty_panel(self.lineage_fig,'lineage_ax',self.lineage_canvas,'Run a GEO or local expression analysis first.'); return
        ax=self._reset_axes(self.lineage_fig,'lineage_ax')
        pub.draw_lineage_trajectory(ax,self.lineage_scores,LINEAGE_PANELS)
        self.lineage_fig.tight_layout(); self.lineage_canvas.draw()

    def _draw_lineage_heatmap(self):
        if self.lineage_ranks is None or self.lineage_ranks.empty:
            self._empty_panel(self.heat_fig,'heat_ax',self.heat_canvas,'Run an analysis first.\nNo lineage marker matrix is available yet.'); return
        ax=self._reset_axes(self.heat_fig,'heat_ax')
        pub.draw_marker_heatmap(self.heat_fig,ax,self.lineage_ranks,LINEAGE_PANELS)
        self.heat_fig.subplots_adjust(left=.25,right=.88,bottom=.17,top=.98); self.heat_canvas.draw()

    def _export_lineage_scores(self):
        if self.lineage_scores is None or self.lineage_scores.empty:
            return messagebox.showwarning('Lineage Analysis','Run an analysis first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Lineage_Scores.xlsx',defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx'),('CSV','*.csv')])
        if not p:return
        try:
            if str(p).lower().endswith('.csv'): self.lineage_scores.to_csv(p)
            else:
                with pd.ExcelWriter(p,engine='openpyxl') as w:
                    self.lineage_scores.to_excel(w,sheet_name='Lineage_Scores')
                    if self.lineage_ranks is not None:self.lineage_ranks.to_excel(w,sheet_name='Marker_Ranks')
            messagebox.showinfo('Export complete',f'Lineage results saved to:\n{p}')
        except Exception as e:messagebox.showerror('Export failed',f'{type(e).__name__}: {e}')

    def _save_state_probability(self):
        if self.current is None or self.current.empty:
            return messagebox.showwarning('State probability','Run an analysis first.')
        self._save_multi(pub.fig_state_trajectory(self.current),'StemScore_Cell_State_Probability_Trajectory','Save cell-state trajectory figure')

    def _save_lineage_trajectory(self):
        if self.lineage_scores is None or self.lineage_scores.empty:return messagebox.showwarning('Lineage Analysis','Run an analysis first.')
        self._save_multi(pub.fig_lineage_trajectory(self.lineage_scores,LINEAGE_PANELS),'StemScore_Lineage_Trajectory','Save lineage trajectory figure')

    def _save_lineage_heatmap(self):
        if self.lineage_ranks is None or self.lineage_ranks.empty:return messagebox.showwarning('Lineage Analysis','Run an analysis first.')
        self._save_multi(pub.fig_marker_heatmap(self.lineage_ranks,LINEAGE_PANELS),'StemScore_Lineage_Marker_Heatmap','Save lineage marker heatmap figure')

    def _contrib_ui(self):
        f=self.contrib
        ttk.Label(f,text='Gene Contribution / Marker Analysis',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(f,text='Shows frozen-model feature contributions for the selected sample. Contributions explain the model prediction; they are not causal gene effects.',wraplength=1200).pack(anchor='w',pady=4)
        top=ttk.Frame(f); top.pack(fill='x',pady=8)
        ttk.Label(top,text='Sample:').pack(side='left')
        self.contrib_sample=tk.StringVar(value='')
        self.contrib_combo=ttk.Combobox(top,textvariable=self.contrib_sample,state='readonly',width=28)
        self.contrib_combo.pack(side='left',padx=6); self.contrib_combo.bind('<<ComboboxSelected>>',lambda e:self._refresh_contribution())
        ttk.Button(top,text='Refresh Analysis',command=self._refresh_contribution).pack(side='left',padx=6)
        ttk.Button(top,text='Export Gene Contributions',command=self._export_gene_contrib).pack(side='left',padx=6)
        ttk.Button(top,text='Export Marker Analysis',command=self._export_marker_analysis).pack(side='left',padx=6)
        self.contrib_status=ttk.Label(f,text='Run a GEO or local expression analysis first.')
        self.contrib_status.pack(anchor='w',pady=4)

        # Use a vertical PanedWindow so BOTH analysis tables remain accessible instead of
        # the lower Marker Analysis table being pushed below the visible window.
        panes=ttk.PanedWindow(f,orient='vertical')
        panes.pack(fill='both',expand=True,pady=4)

        top_pane=ttk.Frame(panes,padding=(0,2,0,4))
        ttk.Label(top_pane,text='Top model contributions',font=('Segoe UI',10,'bold')).pack(anchor='w')
        tf=ttk.Frame(top_pane); tf.pack(fill='both',expand=True,pady=2)
        cols=('Gene','Rank percentile','Standardized value','Contribution','Direction','Class')
        self.contrib_tree=ttk.Treeview(tf,columns=cols,show='headings')
        vs=ttk.Scrollbar(tf,orient='vertical',command=self.contrib_tree.yview); hs=ttk.Scrollbar(tf,orient='horizontal',command=self.contrib_tree.xview)
        self.contrib_tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        widths={'Gene':170,'Rank percentile':130,'Standardized value':150,'Contribution':130,'Direction':190,'Class':140}
        for c in cols:self.contrib_tree.heading(c,text=c); self.contrib_tree.column(c,width=widths.get(c,150),anchor='center')
        self.contrib_tree.grid(row=0,column=0,sticky='nsew'); vs.grid(row=0,column=1,sticky='ns'); hs.grid(row=1,column=0,sticky='ew'); tf.rowconfigure(0,weight=1); tf.columnconfigure(0,weight=1)

        marker_pane=ttk.Frame(panes,padding=(0,4,0,0))
        ttk.Label(marker_pane,text='Marker Analysis',font=('Segoe UI',10,'bold')).pack(anchor='w')
        ttk.Label(marker_pane,text='Fixed biological marker panels; presence/rank is descriptive and does not by itself establish cell identity.',wraplength=1200).pack(anchor='w')
        mf=ttk.Frame(marker_pane); mf.pack(fill='both',expand=True,pady=2)
        mcols=('Panel','Gene','Present','Rank percentile','Interpretation')
        self.marker_tree=ttk.Treeview(mf,columns=mcols,show='headings')
        mvs=ttk.Scrollbar(mf,orient='vertical',command=self.marker_tree.yview); mhs=ttk.Scrollbar(mf,orient='horizontal',command=self.marker_tree.xview)
        self.marker_tree.configure(yscrollcommand=mvs.set,xscrollcommand=mhs.set)
        mwidths={'Panel':150,'Gene':150,'Present':90,'Rank percentile':140,'Interpretation':260}
        for c in mcols:self.marker_tree.heading(c,text=c); self.marker_tree.column(c,width=mwidths.get(c,150),anchor='center')
        self.marker_tree.grid(row=0,column=0,sticky='nsew'); mvs.grid(row=0,column=1,sticky='ns'); mhs.grid(row=1,column=0,sticky='ew'); mf.rowconfigure(0,weight=1); mf.columnconfigure(0,weight=1)

        panes.add(top_pane,weight=3)
        panes.add(marker_pane,weight=2)

    def _sync_contribution_samples(self):
        if self.current is None or len(self.current.index)==0:
            self.contrib_combo['values']=()
            self.contrib_sample.set('')
            return
        samples=[str(x) for x in self.current.index]
        self.contrib_combo['values']=samples
        selected=self.contrib_sample.get()
        if selected not in samples:
            selected=samples[0]
            self.contrib_sample.set(selected)
        return selected

    def _refresh_contribution(self):
        if self.expr is None or self.current is None:
            self.contrib_status.configure(text='Run a GEO or local expression analysis first.')
            return
        try:
            selected=self._sync_contribution_samples()
            if not selected: return
            prepared=prepare_expression(self.expr)
            shared=[g for g in self.bundle.rank_universe if g in prepared.index]
            ranks=rank_normalize(prepared, shared)
            genes=list(self.prediction_genes)
            x=ranks.reindex(index=genes,columns=[selected]).fillna(0.5).iloc[:,0].astype(float)
            mdl=self.prediction_model
            if not hasattr(mdl,'named_steps') or 'scale' not in mdl.named_steps or 'logreg' not in mdl.named_steps:
                raise ValueError('Frozen model does not expose the expected scaler + logistic-regression components.')
            scaler=mdl.named_steps['scale']; clf=mdl.named_steps['logreg']
            scale=np.asarray(scaler.scale_,dtype=float); mean=np.asarray(scaler.mean_,dtype=float)
            z=(x.to_numpy(dtype=float)-mean)/np.where(scale==0,1.0,scale)
            classes=[str(c) for c in clf.classes_]
            pred=str(self.current.loc[selected,'Predicted_State'])
            cls=pred if pred in classes else classes[int(np.argmax(self.current.loc[selected,classes].to_numpy(dtype=float)))]
            j=classes.index(cls)
            contrib=np.asarray(clf.coef_[j],dtype=float)*z
            order=np.argsort(np.abs(contrib))[::-1][:50]
            rows=[]
            for i in order:
                g=genes[i]; direction='Supports '+cls if contrib[i]>0 else 'Opposes '+cls if contrib[i]<0 else 'Neutral'
                rows.append({'Gene':g,'Rank percentile':float(x.iloc[i]),'Standardized value':float(z[i]),'Contribution':float(contrib[i]),'Direction':direction,'Class':cls})
            self.gene_contrib=pd.DataFrame(rows)
            for item in self.contrib_tree.get_children(): self.contrib_tree.delete(item)
            for r in rows:self.contrib_tree.insert('', 'end', values=(r['Gene'],f"{r['Rank percentile']:.4f}",f"{r['Standardized value']:.4f}",f"{r['Contribution']:.5f}",r['Direction'],r['Class']))
            panels={'Pluripotency':PLURIPOTENCY_GENES,'Proliferation':PROLIFERATION_GENES}
            for k,v in LINEAGE_PANELS.items(): panels[k]=v
            marker_rows=[]
            for panel,plist in panels.items():
                for g in plist:
                    present=g in ranks.index
                    rp=float(ranks.loc[g,selected]) if present else np.nan
                    interp='Present' if present else 'Missing'
                    marker_rows.append({'Panel':panel,'Gene':g,'Present':present,'Rank percentile':rp,'Interpretation':interp})
            self.marker_analysis=pd.DataFrame(marker_rows)
            for item in self.marker_tree.get_children(): self.marker_tree.delete(item)
            for r in marker_rows:self.marker_tree.insert('', 'end', values=(r['Panel'],r['Gene'],'Yes' if r['Present'] else 'No','—' if pd.isna(r['Rank percentile']) else f"{r['Rank percentile']:.4f}",r['Interpretation']))
            self.contrib_status.configure(text=f'Sample: {selected} | Predicted state: {pred} | Showing top {len(rows)} absolute model contributions.')
        except Exception as e:
            self.gene_contrib=None; self.marker_analysis=None
            self.contrib_status.configure(text=f'Gene contribution analysis unavailable: {type(e).__name__}: {e}')

    def _export_gene_contrib(self):
        if self.gene_contrib is None or self.gene_contrib.empty:return messagebox.showwarning('Gene Contribution','Run an analysis and select a sample first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Gene_Contributions.xlsx',defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx'),('CSV','*.csv')])
        if not p:return
        try:
            if str(p).lower().endswith('.csv'): self.gene_contrib.to_csv(p,index=False)
            else:
                with pd.ExcelWriter(p,engine='openpyxl') as w:self.gene_contrib.to_excel(w,index=False,sheet_name='Gene_Contributions')
            messagebox.showinfo('Export complete',f'Gene contribution results saved to:\n{p}')
        except Exception as e:messagebox.showerror('Export failed',f'{type(e).__name__}: {e}')

    def _export_marker_analysis(self):
        if self.marker_analysis is None or self.marker_analysis.empty:return messagebox.showwarning('Marker Analysis','Run an analysis first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Marker_Analysis.xlsx',defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx'),('CSV','*.csv')])
        if not p:return
        try:
            if str(p).lower().endswith('.csv'): self.marker_analysis.to_csv(p,index=False)
            else:
                with pd.ExcelWriter(p,engine='openpyxl') as w:self.marker_analysis.to_excel(w,index=False,sheet_name='Marker_Analysis')
            messagebox.showinfo('Export complete',f'Marker analysis saved to:\n{p}')
        except Exception as e:messagebox.showerror('Export failed',f'{type(e).__name__}: {e}')

    def _micro_ui(self):
        f=self.micro
        ttk.Label(f,text='StemScore Microscopy AI',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(f,text='Quantitative stem-cell image QC and morphology analysis. Biological-state classification is reported as exploratory until independently validated.',wraplength=1100).pack(anchor='w',pady=5)
        row=ttk.Frame(f); row.pack(fill='x',pady=8)
        self.micro_paths=[]
        ttk.Button(row,text='Select Microscopy Images',style='Big.TButton',command=self.micro_browse).pack(side='left')
        ttk.Button(row,text='Analyze All Images',style='Big.TButton',command=self.micro_analyze).pack(side='left',padx=8)
        ttk.Button(row,text='Clear',command=self.micro_clear).pack(side='left'); ttk.Button(row,text='Open Reference Library',command=self.micro_open_refs).pack(side='left',padx=8)
        self.micro_info=ttk.Label(f,text='No microscopy images selected.'); self.micro_info.pack(anchor='w',pady=4)

        # Keep export controls ABOVE the expanding results pane so they are always visible.
        exportbar=ttk.LabelFrame(f,text='SAVE / EXPORT MICROSCOPY RESULTS')
        exportbar.pack(fill='x',pady=(2,6))
        ttk.Button(exportbar,text='SAVE RESULT FILE (ZIP)',style='Big.TButton',command=self.micro_save_complete_zip).pack(side='left',padx=5,pady=5)
        ttk.Button(exportbar,text='Save Excel',command=self.micro_save_xlsx).pack(side='left',padx=5,pady=5)
        ttk.Button(exportbar,text='Save CSV',command=self.micro_save_csv).pack(side='left',padx=5,pady=5)
        ttk.Button(exportbar,text='Save Graph PNG',command=self.micro_save_plot).pack(side='left',padx=5,pady=5)
        ttk.Button(exportbar,text='Save PDF Report',command=self.micro_report).pack(side='left',padx=5,pady=5)
        ttk.Button(exportbar,text='Open Results Folder',command=self.micro_open_results).pack(side='left',padx=5,pady=5)
        ttk.Label(exportbar,text='After Analyze All Images, click SAVE RESULT FILE (ZIP) to save one complete research result file.',wraplength=520).pack(side='left',padx=10)

        pan=ttk.Panedwindow(f,orient='horizontal'); pan.pack(fill='both',expand=True,pady=8)
        left=ttk.Frame(pan); right=ttk.Frame(pan); pan.add(left,weight=3); pan.add(right,weight=2)
        cols=('Image','Day','Width','Height','Bit depth','Sharpness','Foreground %','Objects','Median area px2','Circularity','Solidity','Eccentricity','Area CV','Morphology','QC','Microscopy State')
        tf=ttk.Frame(left); tf.pack(fill='both',expand=True)
        self.micro_tree=ttk.Treeview(tf,columns=cols,show='headings')
        vs=ttk.Scrollbar(tf,orient='vertical',command=self.micro_tree.yview); hs=ttk.Scrollbar(tf,orient='horizontal',command=self.micro_tree.xview)
        self.micro_tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        for c in cols: self.micro_tree.heading(c,text=c); self.micro_tree.column(c,width=105,anchor='center')
        self.micro_tree.grid(row=0,column=0,sticky='nsew'); vs.grid(row=0,column=1,sticky='ns'); hs.grid(row=1,column=0,sticky='ew'); tf.rowconfigure(0,weight=1); tf.columnconfigure(0,weight=1)
        ttk.Label(right,text='Trajectory Graph',font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(0,4))
        self.micro_fig=plt.Figure(figsize=(6.4,4.2),dpi=100); self.micro_ax=self.micro_fig.add_subplot(111); self.micro_ax.set_title('Microscopy morphology trajectory'); self.micro_ax.set_xlabel('Day'); self.micro_ax.set_ylabel('Mean morphology index'); self.micro_canvas=FigureCanvasTkAgg(self.micro_fig,master=right); self.micro_canvas.get_tk_widget().pack(fill='x',expand=False); self.micro_text=tk.Text(right,wrap='word',height=14); self.micro_text.pack(fill='both',expand=True)
        self.micro_text.insert('end','Microscopy AI workflow:\n\n1. Image QC\n2. Background/structure segmentation candidate\n3. Morphology measurements\n4. QC flags\n5. Day-aware summary when day is present\n\nScientific note: foreground fraction is not validated confluency; object count is not validated cell count; morphology index is descriptive, not a biological-state score.\n')
        self.micro_results=None

    def micro_browse(self):
        paths=filedialog.askopenfilenames(filetypes=[('Microscopy images','*.tif *.tiff *.png *.jpg *.jpeg *.bmp'),('All files','*.*')])
        if paths:
            self.micro_paths=list(paths); self.micro_info.configure(text=f'{len(paths)} microscopy images selected.'); self.status.set('Microscopy images ready for analysis.')

    def micro_open_refs(self):
        ref=BASE/'microscopy_reference_library'
        if ref.exists():
            try:
                os.startfile(ref) if os.name=='nt' else webbrowser.open(ref.as_uri())
            except Exception as e: messagebox.showerror('Reference Library',str(e))
        else: messagebox.showwarning('Reference Library','The bundled microscopy reference library was not found.')

    def micro_clear(self):
        self.micro_paths=[]; self.micro_results=None
        for x in self.micro_tree.get_children(): self.micro_tree.delete(x)
        self.micro_info.configure(text='No microscopy images selected.'); self.micro_text.delete('1.0','end'); self.micro_text.insert('end','No microscopy analysis yet.\n'); self.micro_ax.clear(); self.micro_ax.set_title('Microscopy morphology trajectory'); self.micro_ax.set_xlabel('Day'); self.micro_ax.set_ylabel('Mean morphology index'); self.micro_canvas.draw_idle()

    def micro_analyze(self):
        if not self.micro_paths: return messagebox.showwarning('Microscopy AI','Select one or more microscopy images first.')
        try:
            overlay_dir=OUT/'microscopy_overlays'
            df=analyze_paths(self.micro_paths,overlay_dir=overlay_dir)
            self.micro_results=df
            for x in self.micro_tree.get_children(): self.micro_tree.delete(x)
            for _,r in df.iterrows():
                vals=(r['Image'], '—' if pd.isna(r['Day']) else f"D{r['Day']:g}", int(r['Width']),int(r['Height']),int(r['Bit_depth']),f"{r['Sharpness']:.5f}",f"{r['Foreground_fraction']*100:.2f}",int(r['Object_count']),f"{r['Median_object_area_px2']:.1f}",f"{r['Circularity']:.3f}",f"{r['Solidity']:.3f}",f"{r['Eccentricity']:.3f}",f"{r['Area_CV']:.3f}",f"{r['Morphology_Index']:.3f}",r['QC'],'NOT ASSIGNED — microscopy classifier not independently validated')
                self.micro_tree.insert('', 'end', values=vals)
            pass_n=int((df['QC']=='PASS').sum()); review_n=len(df)-pass_n
            self.micro_info.configure(text=f'{len(df)} images analyzed | PASS: {pass_n} | REVIEW: {review_n}')
            self.micro_text.delete('1.0','end')
            self.micro_text.insert('end','StemScore Microscopy AI — Automatic Analysis\n\n')
            self.micro_text.insert('end','Microscopy biological state: NOT ASSIGNED. The current microscopy module measures morphology/QC only; it does not claim Pluripotent, Progenitor, or Differentiated from image appearance because an independently labelled and held-out microscopy classifier has not been validated.\n\n')
            self.micro_text.insert('end',f'Images analyzed: {len(df)}\nPASS: {pass_n}\nREVIEW: {review_n}\n\n')
            self.micro_ax.clear(); self.micro_ax.set_title('Microscopy morphology trajectory'); self.micro_ax.set_xlabel('Day'); self.micro_ax.set_ylabel('Mean morphology index')
            if df['Day'].notna().any():
                self.micro_text.insert('end','Day-level summary:\n')
                summ=df[df['Day'].notna()].groupby('Day').agg(N=('Image','size'),Mean_Foreground=('Foreground_fraction','mean'),Median_Objects=('Object_count','median'),Mean_Sharpness=('Sharpness','mean'),Mean_Morphology=('Morphology_Index','mean')).reset_index()
                self.micro_text.insert('end',summ.to_string(index=False))
                self.micro_ax.plot(summ['Day'],summ['Mean_Morphology'],marker='o')
                self.micro_ax.grid(True,alpha=0.25)
            else:
                self.micro_ax.text(0.5,0.5,'Day metadata unavailable\nfor selected images',ha='center',va='center',transform=self.micro_ax.transAxes)
            self.micro_canvas.draw_idle()
            self.status.set('Microscopy analysis complete.')
        except Exception as e: messagebox.showerror('Microscopy AI',str(e))

    def _micro_make_excel(self, p):
        """Write a complete microscopy workbook and fail loudly if it cannot be saved."""
        p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
        with pd.ExcelWriter(p,engine='openpyxl') as writer:
            self.micro_results.to_excel(writer,index=False,sheet_name='Image_Results')
            daydf=self.micro_results[self.micro_results['Day'].notna()]
            if not daydf.empty:
                summ=daydf.groupby('Day').agg(N=('Image','size'),Mean_Foreground=('Foreground_fraction','mean'),Median_Objects=('Object_count','median'),Mean_Sharpness=('Sharpness','mean'),Mean_Morphology=('Morphology_Index','mean')).reset_index()
            else:
                summ=pd.DataFrame(columns=['Day','N','Mean_Foreground','Median_Objects','Mean_Sharpness','Mean_Morphology'])
            summ.to_excel(writer,index=False,sheet_name='Day_Summary')
            pd.DataFrame([
                {'Item':'Microscopy biological state','Result':'NOT ASSIGNED'},
                {'Item':'Reason','Result':'No independently validated microscopy-only Pluripotent/Progenitor/Differentiated classifier is included in this version.'},
                {'Item':'Morphology Index','Result':'Descriptive exploratory metric; not a biological-state score.'},
                {'Item':'Images analyzed','Result':len(self.micro_results)},
                {'Item':'QC PASS','Result':int((self.micro_results['QC']=='PASS').sum())},
                {'Item':'QC REVIEW','Result':int((self.micro_results['QC']!='PASS').sum())},
            ]).to_excel(writer,index=False,sheet_name='State_Interpretation')
        # Add graph as a dedicated worksheet. Do not silently suppress failures.
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl import load_workbook
        tmp=p.with_name('_StemScore_temp_trajectory.png')
        self.micro_fig.savefig(tmp,dpi=200,bbox_inches='tight')
        try:
            wb=load_workbook(p)
            ws=wb.create_sheet('Trajectory_Graph')
            ws['A1']='Microscopy morphology trajectory'
            ws['A2']='Descriptive morphology index; not a validated biological-state score.'
            ws.add_image(XLImage(str(tmp)),'A4')
            wb.save(p)
        finally:
            tmp.unlink(missing_ok=True)
        return p

    def micro_open_results(self):
        OUT.mkdir(parents=True,exist_ok=True)
        try:
            os.startfile(OUT) if os.name=='nt' else webbrowser.open(OUT.as_uri())
        except Exception as e:
            messagebox.showerror('Results Folder',str(e))

    def micro_save_complete_zip(self):
        if self.micro_results is None:
            return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        p=filedialog.asksaveasfilename(
            initialdir=OUT,
            initialfile='StemScore_Microscopy_Complete_Results.zip',
            defaultextension='.zip',
            filetypes=[('ZIP result file','*.zip')])
        if not p:
            return
        p=Path(p)
        work=OUT/'_microscopy_export_staging'
        try:
            if work.exists(): shutil.rmtree(work)
            work.mkdir(parents=True,exist_ok=True)
            self.micro_results.to_csv(work/'StemScore_microscopy_results.csv',index=False)
            self._micro_make_excel(work/'StemScore_microscopy_results.xlsx')
            self.micro_fig.savefig(work/'StemScore_microscopy_trajectory.png',dpi=600,bbox_inches='tight')
            self._micro_write_pdf(work/'StemScore_Microscopy_Report.pdf')
            if (OUT/'microscopy_overlays').exists():
                shutil.copytree(OUT/'microscopy_overlays',work/'microscopy_overlays',dirs_exist_ok=True)
            (work/'README.txt').write_text(
                'StemScore AI Microscopy AI complete result export.\n\n'
                'Includes image-level morphology/QC results, day summary, trajectory graph, PDF report, and segmentation overlays when available.\n'
                'Microscopy biological-state labels are not assigned unless independently validated.\n',
                encoding='utf-8')
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
                for q in work.rglob('*'):
                    if q.is_file(): z.write(q,q.relative_to(work))
            self.status.set(f'Microscopy result file saved: {p}')
            messagebox.showinfo('Microscopy result saved',f'Complete microscopy result file saved to:\n\n{p}')
        except Exception as e:
            messagebox.showerror('Microscopy export failed',f'{type(e).__name__}: {e}\n\nNo incomplete result file was reported as successful.')
        finally:
            if work.exists(): shutil.rmtree(work,ignore_errors=True)

    def micro_export_all(self):
        if self.micro_results is None:
            return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        folder=OUT/'microscopy_latest_results'
        folder.mkdir(parents=True,exist_ok=True)
        try:
            csvp=folder/'StemScore_microscopy_results.csv'
            self.micro_results.to_csv(csvp,index=False)
            xlsxp=self._micro_make_excel(folder/'StemScore_microscopy_results.xlsx')
            plotp=folder/'StemScore_microscopy_trajectory.png'
            self.micro_fig.savefig(plotp,dpi=600,bbox_inches='tight')
            # Create a concise PDF report using the existing report generator without another dialog.
            pdfp=folder/'StemScore_Microscopy_Report.pdf'
            self._micro_write_pdf(pdfp)
            zipp=folder/'StemScore_Microscopy_Complete_Results.zip'
            with zipfile.ZipFile(zipp,'w',zipfile.ZIP_DEFLATED) as z:
                for q in folder.iterdir():
                    if q.is_file() and q.name != zipp.name:
                        z.write(q,q.name)
            self.status.set(f'Microscopy results exported: {folder}')
            messagebox.showinfo('Microscopy export complete',
                'All microscopy result files were saved automatically.\\n\\n'
                f'Folder:\\n{folder}\\n\\n'
                'Files: CSV, Excel, Graph PNG, PDF and ZIP.')
            self.micro_open_results()
        except Exception as e:
            messagebox.showerror('Microscopy export failed',
                f'Could not export the microscopy results.\\n\\n{type(e).__name__}: {e}\\n\\n'
                'Try Export Excel or CSV separately, or send this error to the developer.')

    def micro_save_csv(self):
        if self.micro_results is None: return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_microscopy_results.csv',defaultextension='.csv')
        if p: self.micro_results.to_csv(p,index=False); messagebox.showinfo('Saved',p)

    def micro_save_xlsx(self):
        if self.micro_results is None: return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_microscopy_results.xlsx',defaultextension='.xlsx',filetypes=[('Excel workbook','*.xlsx')])
        if p:
            try:
                self._micro_make_excel(p)
                messagebox.showinfo('Excel created',f'Microscopy Excel results saved to:\n{p}')
            except Exception as e:
                messagebox.showerror('Excel export failed',f'{type(e).__name__}: {e}')

    def micro_save_plot(self):
        if self.micro_results is None: return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        self._save_multi(self.micro_fig,'StemScore_microscopy_trajectory','Save microscopy trajectory figure')

    def micro_export_bundle(self):
        if self.micro_results is None: return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        folder=OUT/'microscopy_export_bundle'
        folder.mkdir(parents=True,exist_ok=True)
        csvp=folder/'StemScore_microscopy_results.csv'; self.micro_results.to_csv(csvp,index=False)
        xlsxp=folder/'StemScore_microscopy_results.xlsx'
        with pd.ExcelWriter(xlsxp,engine='openpyxl') as writer:
            self.micro_results.to_excel(writer,index=False,sheet_name='Image_Results')
            if self.micro_results['Day'].notna().any():
                summ=self.micro_results[self.micro_results['Day'].notna()].groupby('Day').agg(N=('Image','size'),Mean_Foreground=('Foreground_fraction','mean'),Median_Objects=('Object_count','median'),Mean_Sharpness=('Sharpness','mean'),Mean_Morphology=('Morphology_Index','mean')).reset_index()
                summ.to_excel(writer,index=False,sheet_name='Day_Summary')
            pd.DataFrame([{'Item':'Microscopy biological state','Result':'NOT ASSIGNED'},{'Item':'Reason','Result':'Microscopy-only state classifier is not independently validated.'}]).to_excel(writer,index=False,sheet_name='State_Interpretation')
        try:
            from openpyxl.drawing.image import Image as XLImage
            tmp_plot=xlsxp.with_name('_trajectory.png'); self.micro_fig.savefig(tmp_plot,dpi=200,bbox_inches='tight')
            from openpyxl import load_workbook
            wb=load_workbook(xlsxp); ws=wb.create_sheet('Trajectory_Graph'); ws['A1']='Microscopy morphology trajectory'; ws['A2']='Descriptive morphology index; not a validated biological-state score.'; ws.add_image(XLImage(str(tmp_plot)),'A4'); wb.save(xlsxp); tmp_plot.unlink(missing_ok=True)
        except Exception: pass
        plotp=folder/'StemScore_microscopy_trajectory.png'; self.micro_fig.savefig(plotp,dpi=600,bbox_inches='tight')
        if (OUT/'microscopy_overlays').exists():
            shutil.copytree(OUT/'microscopy_overlays',folder/'microscopy_overlays',dirs_exist_ok=True)
        readm=folder/'README.txt'; readm.write_text('StemScore Microscopy AI export bundle\n\nContains image-level results, day-level summary when available, trajectory plot, and segmentation overlays. Morphology measurements are exploratory and are not a validated biological-state classifier.\n',encoding='utf-8')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Microscopy_Complete_Results.zip',defaultextension='.zip',filetypes=[('ZIP archive','*.zip')])
        if p:
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
                for q in folder.rglob('*'):
                    if q.is_file(): z.write(q,q.relative_to(folder))
            messagebox.showinfo('Export complete',p)

    def _micro_write_pdf(self,p):
        p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
        styles=getSampleStyleSheet(); doc=SimpleDocTemplate(str(p),pagesize=landscape(A4),rightMargin=24,leftMargin=24,topMargin=24,bottomMargin=24)
        story=[Paragraph('StemScore AI — Stem-Cell Microscopy AI Report',styles['Title']),Spacer(1,8),Paragraph(f'Images analyzed: {len(self.micro_results)}',styles['Normal']),Paragraph('Purpose: quantitative microscopy QC and morphology analysis.',styles['Normal']),Spacer(1,10)]
        story.append(Paragraph('Scientific status: morphology measurements are exploratory. Foreground fraction is not validated confluency, object count is not validated cell count, and Morphology Index is descriptive. A validated image-only Pluripotent/Progenitor/Differentiated classifier requires independent labelled microscopy data.',styles['BodyText']))
        story.append(Spacer(1,10))
        cols=['Image','Day','Width','Height','Sharpness','Foreground %','Objects','Median area','Circularity','Solidity','Eccentricity','Morphology','QC']
        rows=[cols]
        for _,r in self.micro_results.iterrows():
            rows.append([str(r['Image']),('—' if pd.isna(r['Day']) else f"D{r['Day']:g}"),str(int(r['Width'])),str(int(r['Height'])),f"{r['Sharpness']:.5f}",f"{r['Foreground_fraction']*100:.2f}",str(int(r['Object_count'])),f"{r['Median_object_area_px2']:.1f}",f"{r['Circularity']:.3f}",f"{r['Solidity']:.3f}",f"{r['Eccentricity']:.3f}",f"{r['Morphology_Index']:.3f}",str(r['QC'])])
        t=Table(rows,repeatRows=1); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1f4e78')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.3,colors.grey),('FONTSIZE',(0,0),(-1,-1),7),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story.append(t); story.append(Spacer(1,12)); doc.build(story)
        return p

    def micro_report(self):
        if self.micro_results is None: return messagebox.showwarning('Microscopy AI','Analyze microscopy images first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Microscopy_Report.pdf',defaultextension='.pdf',filetypes=[('PDF report','*.pdf')])
        if not p:return
        try:
            self._micro_write_pdf(p); messagebox.showinfo('PDF created',f'Microscopy PDF report saved to:\n{p}')
        except Exception as e:
            messagebox.showerror('PDF export failed',f'{type(e).__name__}: {e}')

    def save_csv(self):
        if self.current is None:return messagebox.showwarning('Results','Run an analysis first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_results.csv',defaultextension='.csv')
        if p:self.current.to_csv(p,index=True); messagebox.showinfo('Saved',p)
    def pdf(self):
        if self.current is None:return messagebox.showwarning('Results','Run an analysis first.')
        p=filedialog.asksaveasfilename(initialdir=OUT,initialfile='StemScore_Report.pdf',defaultextension='.pdf')
        if not p:return
        styles=getSampleStyleSheet(); doc=SimpleDocTemplate(p,pagesize=landscape(A4),rightMargin=24,leftMargin=24,topMargin=24,bottomMargin=24)
        story=[Paragraph('StemScore AI — Stem-Cell Gene Expression Research Report',styles['Title']),Spacer(1,8),Paragraph(f'Source: {self.source}',styles['Normal']),Paragraph(f"Analysis mode: {self.meta.get('analysis_mode','')}",styles['Normal']),Paragraph(f"Genes: {self.meta.get('rank_genes_used', 'n/a'):,} shared | Model coverage: {self.meta.get('model_gene_coverage',0)*100:.1f}%",styles['Normal']),Spacer(1,12)]
        rows=[['Sample','State','P(Pluri)','P(Progenitor)','P(Diff)','Confidence','Pluripotency','Proliferation','Coverage']]
        for idx,r in self.current.iterrows():rows.append([str(idx),str(r.get('Predicted_State','')),f"{float(r.get('Pluripotent',np.nan)):.3f}",f"{float(r.get('Progenitor',np.nan)):.3f}",f"{float(r.get('Differentiated',np.nan)):.3f}",f"{float(r.get('Confidence',np.nan)):.3f}",f"{float(r.get('Pluripotency_Score',np.nan)):.3f}",f"{float(r.get('Proliferation_Score',np.nan)):.3f}" if pd.notna(r.get('Proliferation_Score',np.nan)) else '—',f"{float(r.get('Model_Gene_Coverage',self.meta.get('model_gene_coverage',np.nan)))*100:.1f}%"])
        t=Table(rows,repeatRows=1); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1f4e78')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.4,colors.grey),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story.append(t); story.append(Spacer(1,12)); story.append(Paragraph(f"Identifier type: {self.meta.get('identifier_type','Gene symbol')} | Mapped IDs: {self.meta.get('mapped',0):,} | Shared genes: {self.meta.get('shared_gene_count',self.meta.get('rank_genes_used','n/a')):,} | Uncertainty threshold: {self.meta.get('uncertainty_threshold',0.60):.2f}",styles['Normal'])); story.append(Spacer(1,8)); story.append(Paragraph('Model provenance: frozen StemScore core trained independently on GSE304806 + GSE314132. Uploaded data are not used to retrain the classifier. Missing model genes, when present, use neutral percentile rank 0.5 and are reported through model coverage.',styles['BodyText'])); story.append(Spacer(1,8)); story.append(Paragraph('Scientific interpretation: the state is a model-derived classification. Agreement with GEO study metadata is validation evidence, not a substitute for biological ground truth. Low coverage, marker-screening mode, or uncertain predictions must be treated cautiously.',styles['BodyText']))
        doc.build(story); messagebox.showinfo('PDF created',p)

def _install_crash_logging():
    """A windowed EXE swallows errors and can close silently. Write every error/crash to a log file instead."""
    import sys, faulthandler
    log=OUT/'StemScoreAI_crash_log.txt'
    try:
        fh=open(log,'a',buffering=1,encoding='utf-8'); fh.write(f"\n=== session {datetime.now().isoformat(timespec='seconds')} | {APP_VERSION} ===\n")
        faulthandler.enable(file=fh, all_threads=True)   # hard crashes (native code) leave a traceback here
        _install_crash_logging._fh=fh
    except Exception: pass
    def _log(exc_type,exc,tb):
        try:
            with open(log,'a',encoding='utf-8') as f: f.write(''.join(traceback.format_exception(exc_type,exc,tb)))
        except Exception: pass
    sys.excepthook=_log
    return log,_log

if __name__=='__main__':
    _log_path,_log_fn=_install_crash_logging()
    root=tk.Tk()
    def _tk_error(exc_type,exc,tb):
        _log_fn(exc_type,exc,tb)
        try: messagebox.showerror('StemScore AI error',f'{exc_type.__name__}: {exc}\n\nDetails saved to:\n{_log_path}')
        except Exception: pass
    root.report_callback_exception=_tk_error
    App(root); root.mainloop()
