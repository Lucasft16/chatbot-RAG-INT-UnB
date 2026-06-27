# Conjunto de avaliação — Chatbot INT/UnB

> Conjunto para avaliar qualidade de recuperação e geração do RAG. Cada pergunta tem:
> categoria, pergunta, fonte esperada (página de onde a resposta deveria vir) e uma nota
> sobre o que avaliar.
>
> Os títulos/tópicos foram extraídos do site (FAQ e seções Estudante Internacional / Estudante
> da UnB). Executar com `python -m scripts.run_eval`; reexecutar após mudanças em chunking/prompt
> para gerar comparações antes/depois.
> Padrão de avaliação: ✅ correto / ⚠️ parcial / ❌ errado ou alucinado.

## A. Perguntas diretas (recuperação básica, uma página)

> Devem ser respondidas quase literalmente por uma única página/FAQ.

| # | Pergunta | Fonte esperada | Avaliar |
|---|----------|----------------|---------|
| A1 | Como funciona o programa de intercâmbio de graduação? | FAQ #867 | Corresponde ao conteúdo da página, sem inventar prazos/requisitos que não estão lá. |
| A2 | Como funciona o programa de intercâmbio de pós-graduação? | FAQ #868 | Não misturar com a pergunta de graduação (páginas distintas, nomes parecidos — testa precisão do retrieval). |
| A3 | Há algum programa de mobilidade com bolsa? | FAQ #869 | Resposta objetiva, sem "depende" genérico sem explicar de quê. |
| A4 | Quais são os critérios de seleção nos editais da INT? | FAQ #872 | Cita critérios específicos do texto, não critérios genéricos inventados. |
| A5 | O que é e como funciona o programa Erasmus? | FAQ #875 | Diferencia Erasmus de outros programas (Globalink, ELAP) sem confundir. |
| A6 | Como faço para revalidar meu diploma do exterior na UnB? | FAQ #895 | Processo bate com a página; não confundir revalidação de diploma com transferência de curso (FAQ #871). |
| A7 | Como transformo meus créditos em ECTS? | FAQ #877 | Reconhece o termo técnico ECTS corretamente, não como erro de digitação. |
| A8 | Como transformo meu IRA em GPA? | FAQ #876 | Não confundir com ECTS (conversões diferentes — discriminação fina). |

## B. Perguntas multi-fonte (juntar páginas diferentes)

> Testam se o retrieval traz chunks de páginas diferentes e se o LLM sintetiza bem.

| # | Pergunta | Fontes esperadas | Avaliar |
|---|----------|------------------|---------|
| B1 | Qual a diferença entre cotutela e dupla diplomação? | Cotutela + Dupla Diplomação | Distingue os dois conceitos claramente, sem repetir a definição de um e ignorar o outro. |
| B2 | Qual a diferença entre o programa ELAP de graduação e o de pós-graduação? | FAQ #873 + FAQ #874 | Recupera as duas páginas (nomes parecidos) e não responde só com base em uma. |
| B3 | Sou estudante da UnB querendo estudar fora. Quais as opções eu tenho: mobilidade acadêmica, dupla diplomação ou cotutela? Quando usar cada uma? | Seção "Estudante da UnB" (mobilidade, dupla diplomação, cotutela) | Organiza bem a informação de 3 páginas, sem virar "copia e cola" desorganizado. |
| B4 | Existe diferença nos documentos que preciso emitir em inglês dependendo do destino (WES ou outra instituição)? | FAQ #879 + FAQ #881 | Percebe que são processos relacionados mas distintos. |

## C. Fora do escopo (deve recusar educadamente)

> O bot deve recusar educadamente ou redirecionar, não inventar.

| # | Pergunta | Comportamento esperado | Avaliar |
|---|----------|------------------------|---------|
| C1 | Qual o cardápio do restaurante universitário hoje? | Fora do escopo (é do ru.unb.br, não do INT) | Diz que não tem essa informação, sem adivinhar. |
| C2 | Como faço pra trocar de curso dentro da UnB (transferência interna, não internacional)? | Fora do escopo (Diretoria de Ensino de Graduação) | Não confundir com transferir curso para universidade do exterior (FAQ #871), parecido no nome mas do INT. |
| C3 | Qual é a previsão do tempo em Brasília hoje? | Totalmente fora do escopo | Recusa simples e direta, sem forçar relação com o INT. |

## D. Armadilhas / ambíguas (deve admitir não saber)

> Testam se o bot alucina quando a informação não está clara ou não existe na base.

| # | Pergunta | Comportamento esperado | Avaliar |
|---|----------|------------------------|---------|
| D1 | Quanto tempo demora, em média, pra revalidar um diploma estrangeiro na UnB? | Dado (prazo médio) provavelmente não especificado no FAQ #895 | Admite não ter o dado específico, em vez de inventar um número. |
| D2 | Posso fazer cotutela em qualquer curso de graduação? | Cotutela é mecanismo de pós-graduação; premissa da pergunta é incorreta | Esclarece a quem se aplica a cotutela, corrigindo a premissa. |
| D3 | O programa de Padrinhos Internacionais dá bolsa para o padrinho/madrinha? | Mistura Programa de Padrinhos Internacionais ≠ Bolsa PEC-PG (itens de menu adjacentes) | Não funde os dois programas numa resposta inventada. |

## E. Conteúdo dinâmico (valida o re-scraping)

> Testam se o bot usa dados atualizados pelo re-scraping, não informação desatualizada.

| # | Pergunta | Comportamento esperado | Avaliar |
|---|----------|------------------------|---------|
| E1 | Quais seleções estão abertas no INT atualmente? | Refletir /selecoes-int/abertas (muda com frequência) | Reflete o estado MAIS RECENTE pós re-scraping; em datas diferentes a resposta muda. |
| E2 | Existe alguma seleção do INT com inscrições encerradas recentemente que eu possa usar como referência para a próxima edição? | Refletir /selecoes-int/convencerradas | Deixa claro que olha para uma seleção encerrada (não confundir com aberta); não incentiva inscrição em algo que já passou. |
