from django import forms

PERFIS_CHOICES = [
    ('', 'Selecione...'),
    ('1', 'Administrador'),
    ('2', 'Colaborador'),
    ('3', 'Cliente'),
]

SIM_NAO_CHOICES = [('False', 'Nao'), ('True', 'Sim')]


class FormBase(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            classe = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                classe = 'form-check-input'
            field.widget.attrs.setdefault('class', classe)


class LoginForm(FormBase):
    email = forms.EmailField(label='Email', max_length=254)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


class ClienteForm(FormBase):
    nome = forms.CharField(label='Nome da organizacao', max_length=160)
    nif = forms.RegexField(label='NIF', regex=r'^\d{9}$', max_length=9)
    email = forms.EmailField(label='Email geral')
    telefone = forms.CharField(label='Telefone', max_length=30, required=False)
    morada = forms.CharField(label='Morada', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    setor_atividade = forms.CharField(label='Setor de atividade', max_length=100, required=False)
    numero_colaboradores = forms.IntegerField(label='Numero de colaboradores', min_value=0, required=False)
    volume_negocios = forms.DecimalField(label='Volume de negocios', min_value=0, max_digits=14, decimal_places=2, required=False)
    ativo = forms.BooleanField(label='Ativo', required=False, initial=True)


class UtilizadorForm(FormBase):
    perfil_id = forms.ChoiceField(label='Perfil', choices=PERFIS_CHOICES)
    nome = forms.CharField(label='Nome', max_length=120)
    email = forms.EmailField(label='Email')
    telefone = forms.CharField(label='Telefone', max_length=30, required=False)
    nif = forms.RegexField(label='NIF', regex=r'^\d{9}$', max_length=9, required=False)
    password = forms.CharField(label='Password', widget=forms.PasswordInput, min_length=10, required=False,
                               help_text='Obrigatoria na criacao; deixe vazia para manter a atual.')
    ativo = forms.BooleanField(label='Ativo', required=False, initial=True)
    cliente_id = forms.ChoiceField(label='Organizacao cliente', choices=[('', 'Sem associacao')], required=False)

    def __init__(self, *args, clientes=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clientes:
            self.fields['cliente_id'].choices += [(str(c['id']), c['nome']) for c in clientes]

    def clean(self):
        dados = super().clean()
        if not self.initial.get('id') and not dados.get('password'):
            self.add_error('password', 'A password e obrigatoria na criacao.')
        if str(dados.get('perfil_id')) == '3' and not dados.get('cliente_id'):
            self.add_error('cliente_id', 'Um utilizador Cliente deve estar associado a uma organizacao.')
        return dados


class ContactoClienteForm(FormBase):
    tipo = forms.ChoiceField(label='Tipo', choices=[
        ('RESPONSAVEL_SEGURANCA', 'Responsavel de Seguranca'),
        ('CONTACTO_PERMANENTE', 'Contacto Permanente'),
        ('OUTRO', 'Outro'),
    ])
    nome = forms.CharField(label='Nome', max_length=120)
    cargo = forms.CharField(label='Cargo', max_length=100, required=False)
    email = forms.EmailField(label='Email')
    telefone = forms.CharField(label='Telefone', max_length=30, required=False)
    comunicado_cncs = forms.BooleanField(label='Comunicado ao CNCS', required=False)


class AtivoForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    numero_inventario = forms.CharField(label='Numero de inventario', max_length=80, required=False)
    tipo_equipamento = forms.CharField(label='Tipo de equipamento', max_length=100, required=False)
    nome = forms.CharField(label='Nome', max_length=160)
    tipologia = forms.CharField(label='Tipologia', max_length=100, required=False)
    modelo_versao = forms.CharField(label='Modelo/Versao', max_length=160, required=False)
    numero_serie = forms.CharField(label='Numero de serie', max_length=120, required=False)
    fabricante = forms.CharField(label='Fabricante', max_length=120, required=False)
    localizacao = forms.CharField(label='Localizacao', max_length=160, required=False)
    sistema_operativo = forms.CharField(label='Sistema operativo', max_length=120, required=False)
    criticidade = forms.ChoiceField(label='Criticidade', choices=[
        ('RESIDUAL', 'Residual'), ('BAIXA', 'Baixa'), ('MEDIA', 'Media'),
        ('ALTA', 'Alta'), ('CRITICA', 'Critica')])
    endereco_ip = forms.GenericIPAddressField(label='Endereco IP', required=False)
    endereco_mac = forms.CharField(label='Endereco MAC', max_length=17, required=False)
    fqdn = forms.CharField(label='FQDN', max_length=255, required=False)
    servico_suportado = forms.CharField(label='Servico suportado', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    responsavel_nome = forms.CharField(label='Responsavel', max_length=120, required=False)
    responsavel_contacto = forms.CharField(label='Contacto do responsavel', max_length=120, required=False)
    unidade_organica = forms.CharField(label='Unidade organica', max_length=120, required=False)
    aplicacoes_servicos = forms.CharField(label='Aplicacoes/servicos', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    observacoes = forms.CharField(label='Observacoes', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    comunicado_cncs = forms.BooleanField(label='Comunicado ao CNCS', required=False)
    programa_gestao_risco = forms.BooleanField(label='Incluido no programa de gestao de risco', required=False)

    def __init__(self, *args, clientes=None, cliente_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        clientes = clientes or []
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in clientes]
        if cliente_fixo:
            self.fields['cliente_id'].initial = str(cliente_fixo)
            self.fields['cliente_id'].widget = forms.HiddenInput()


class IncidenteForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    codigo = forms.CharField(label='Codigo', max_length=40)
    data_hora_incidente = forms.DateTimeField(label='Data e hora', widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    registado_por = forms.CharField(label='Registado por', max_length=120, required=False)
    departamento = forms.CharField(label='Departamento', max_length=120, required=False)
    tipo_incidente = forms.CharField(label='Tipo de incidente', max_length=100)
    descricao = forms.CharField(label='Descricao', widget=forms.Textarea(attrs={'rows': 4}))
    utilizadores_afetados = forms.IntegerField(label='Utilizadores afetados', min_value=0, initial=0)
    dados_comprometidos = forms.BooleanField(label='Dados comprometidos', required=False)
    sistemas_afetados = forms.CharField(label='Sistemas afetados', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    origem_ataque = forms.CharField(label='Origem do ataque', max_length=160, required=False)
    ip_atacante = forms.GenericIPAddressField(label='IP do atacante', required=False)
    analise_log = forms.CharField(label='Analise de logs', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    resposta_imediata = forms.CharField(label='Resposta imediata', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    medidas_corretivas = forms.CharField(label='Medidas corretivas', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    gravidade = forms.ChoiceField(label='Gravidade', choices=[
        ('RESIDUAL', 'Residual'), ('BAIXA', 'Baixa'), ('MEDIA', 'Media'),
        ('ALTA', 'Alta'), ('CRITICA', 'Critica')])
    probabilidade_reincidencia = forms.ChoiceField(label='Probabilidade de reincidencia', required=False,
        choices=[('', 'Nao definida'), ('BAIXA', 'Baixa'), ('MEDIA', 'Media'), ('ALTA', 'Alta')])
    recomendacoes = forms.CharField(label='Recomendacoes', widget=forms.Textarea(attrs={'rows': 2}), required=False)
    estado = forms.ChoiceField(label='Estado', choices=[('ABERTO', 'Aberto'), ('EM_ANALISE', 'Em analise'), ('ENCERRADO', 'Encerrado')])
    encerrado_em = forms.DateTimeField(label='Data de encerramento', widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}), required=False)
    responsavel_encerramento = forms.CharField(label='Responsavel pelo encerramento', max_length=120, required=False)

    def __init__(self, *args, clientes=None, cliente_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        clientes = clientes or []
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in clientes]
        if cliente_fixo:
            self.fields['cliente_id'].initial = str(cliente_fixo)
            self.fields['cliente_id'].widget = forms.HiddenInput()

    def clean(self):
        dados = super().clean()
        if dados.get('estado') == 'ENCERRADO' and not dados.get('encerrado_em'):
            self.add_error('encerrado_em', 'Indique a data de encerramento.')
        return dados


class AvaliacaoRiscoForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    estado_conformidade_id = forms.ChoiceField(label='Estado de conformidade', choices=[])
    data_avaliacao = forms.DateField(label='Data da avaliacao', widget=forms.DateInput(attrs={'type': 'date'}))
    nivel_risco = forms.ChoiceField(label='Nivel de risco', choices=[
        ('BAIXO', 'Baixo'), ('MEDIO', 'Medio'), ('ALTO', 'Alto'), ('CRITICO', 'Critico')])
    pontuacao = forms.DecimalField(label='Pontuacao (0-100)', min_value=0, max_value=100, max_digits=5, decimal_places=2, required=False)
    resumo = forms.CharField(label='Resumo', widget=forms.Textarea(attrs={'rows': 4}))
    recomendacoes = forms.CharField(label='Recomendacoes', widget=forms.Textarea(attrs={'rows': 4}), required=False)

    def __init__(self, *args, clientes=None, estados=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in (clientes or [])]
        self.fields['estado_conformidade_id'].choices = [(str(e['id']), e['nome']) for e in (estados or [])]


class DocumentoForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    categoria = forms.ChoiceField(label='Categoria', choices=[
        ('DOCUMENTACAO', 'Documentacao'), ('RELATORIO', 'Relatorio'),
        ('PENTEST', 'PenTest'), ('EVIDENCIA', 'Evidencia'), ('OUTRO', 'Outro')])
    titulo = forms.CharField(label='Titulo', max_length=180)
    descricao = forms.CharField(label='Descricao', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    ficheiro = forms.FileField(label='Ficheiro')

    def __init__(self, *args, clientes=None, cliente_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in (clientes or [])]
        if cliente_fixo:
            self.fields['cliente_id'].initial = str(cliente_fixo)
            self.fields['cliente_id'].widget = forms.HiddenInput()

    def clean_ficheiro(self):
        ficheiro = self.cleaned_data['ficheiro']
        permitidos = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/png', 'image/jpeg', 'text/plain',
        }
        if ficheiro.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O ficheiro nao pode exceder 10 MB.')
        if ficheiro.content_type not in permitidos:
            raise forms.ValidationError('Tipo de ficheiro nao permitido.')
        return ficheiro


class PedidoForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    assunto = forms.CharField(label='Assunto', max_length=180)
    descricao = forms.CharField(label='Descricao', widget=forms.Textarea(attrs={'rows': 5}))
    prioridade = forms.ChoiceField(label='Prioridade', choices=[
        ('BAIXA', 'Baixa'), ('NORMAL', 'Normal'), ('ALTA', 'Alta'), ('URGENTE', 'Urgente')])

    def __init__(self, *args, clientes=None, cliente_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in (clientes or [])]
        if cliente_fixo:
            self.fields['cliente_id'].initial = str(cliente_fixo)
            self.fields['cliente_id'].widget = forms.HiddenInput()


class MensagemPedidoForm(FormBase):
    mensagem = forms.CharField(label='Nova mensagem', widget=forms.Textarea(attrs={'rows': 3}))


class AlterarEstadoPedidoForm(FormBase):
    estado_id = forms.ChoiceField(label='Novo estado', choices=[])
    atribuido_a = forms.ChoiceField(label='Atribuir a', choices=[('', 'Sem atribuicao')], required=False)
    observacao = forms.CharField(label='Observacao', widget=forms.Textarea(attrs={'rows': 2}), required=False)

    def __init__(self, *args, estados=None, colaboradores=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado_id'].choices = [(str(e['id']), e['nome']) for e in (estados or [])]
        self.fields['atribuido_a'].choices += [(str(u['id']), u['nome']) for u in (colaboradores or [])]


class ImportarExcelForm(FormBase):
    cliente_id = forms.ChoiceField(label='Cliente', choices=[])
    tipo = forms.ChoiceField(label='Tipo de importacao', choices=[('ATIVOS', 'Ativos tecnologicos'), ('INCIDENTES', 'Incidentes')])
    ficheiro = forms.FileField(label='Ficheiro Excel (.xlsx)')

    def __init__(self, *args, clientes=None, cliente_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente_id'].choices = [(str(c['id']), c['nome']) for c in (clientes or [])]
        if cliente_fixo:
            self.fields['cliente_id'].initial = str(cliente_fixo)
            self.fields['cliente_id'].widget = forms.HiddenInput()

    def clean_ficheiro(self):
        ficheiro = self.cleaned_data['ficheiro']
        if not ficheiro.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('Apenas sao aceites ficheiros .xlsx.')
        if ficheiro.size > 5 * 1024 * 1024:
            raise forms.ValidationError('O ficheiro nao pode exceder 5 MB.')
        return ficheiro
