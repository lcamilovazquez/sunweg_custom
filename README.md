# SunWEG Custom Integration for Home Assistant

Este repositório contém uma integração **não oficial** para o [Home Assistant](https://www.home-assistant.io) que permite monitorar usinas solares cadastradas na plataforma **SunWEG**. A integração autentica com sua conta do SunWEG, obtém um token de acesso e expõe uma série de sensores para acompanhar a produção de energia, potência instantânea, impactos ambientais e economia financeira.

> **Aviso:** Esta integração é um *custom component* e não substitui nenhum componente do Home Assistant Core. Ela não é afiliada à WEG nem ao time oficial do Home Assistant. Use por sua conta e risco.

## Recursos

- **Fluxo de configuração via UI**: configure a integração diretamente na interface do Home Assistant, informando usuário e senha do SunWEG e selecionando a usina desejada.
- **Atualização automática de token**: a integração obtém e renova o token de acesso, dispensando a troca manual no `configuration.yaml`.
- **Sensores agregados** (todas as usinas da conta):
  - Energia gerada hoje, no mês e no total (`kWh`)
  - Potência ativa total (`kW`)
  - Capacidade total (`kW`)
  - Árvores plantadas (unidades)
  - Quilômetros elétricos equivalentes (km)
  - Redução total de CO₂ (toneladas)
  - Economia financeira hoje e acumulada (`R$`)
  - Quantidade de usinas cadastradas
- **Sensores por usina** (para a usina selecionada):
  - Energia diária e mensal da usina (`kWh`)
  - Potência atual da usina (`kW`)
  - Capacidade da usina (`kW`)
  - Yield diário e mensal
- **Agrupamento lógico**: os sensores agregados são agrupados em um “dispositivo” chamado *SunWEG Total*; os sensores específicos ficam no dispositivo da própria usina.

## Instalação

### Via HACS (recomendado)

1. Adicione este repositório no HACS como um repositório personalizado de tipo *Integration*.
2. Instale a integração **SunWEG** pelo HACS.
3. Reinicie o Home Assistant.
4. Acesse **Configurações → Dispositivos e Serviços → Adicionar Integração**, busque por **SunWEG** e siga o assistente para informar usuário, senha e escolher a usina.

> **Observação sobre o ícone:** os arquivos `logo.png` e `icon.png` presentes na raiz deste repositório são usados pelo HACS para exibir um logotipo personalizado. Eles não precisam ser copiados para o Home Assistant; basta mantê‑los no seu GitHub.

### Instalação manual

1. Faça o download deste repositório e copie a pasta `custom_components/sunweg_custom` para o diretório `config/custom_components` da sua instalação do Home Assistant.
2. Reinicie o Home Assistant.
3. Siga os passos do fluxo de configuração via UI (Configurações → Dispositivos e Serviços → Adicionar Integração → SunWEG).

## Como funciona

- **Autenticação:** a integração usa os endpoints de login da API SunWEG para autenticar com seu e‑mail e senha. O token obtido é armazenado e reutilizado até expirar.
- **Coordenador de dados:** um [DataUpdateCoordinator](https://developers.home-assistant.io/docs/data_update_coordinator_index/) gerencia as chamadas periódicas à API (intervalo padrão de 5 minutos), tratando erros de conexão e renovação do token.
- **Criação de sensores:** após a primeira atualização, a integração cria entidades do tipo `sensor` com base nas métricas retornadas pela API, utilizando classes de dispositivo e unidades apropriadas.

## Contribuindo

Sinta‑se à vontade para abrir issues ou enviar *pull requests* para melhorias. Como esta é uma integração de terceiros, testes adicionais são sempre bem‑vindos.
