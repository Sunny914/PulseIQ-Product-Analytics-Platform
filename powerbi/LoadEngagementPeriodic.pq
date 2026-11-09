let
    ExportFolderPath = ExportFolderPath,
    Source = Csv.Document(
        File.Contents(ExportFolderPath & "\fact_engagement_periodic.csv"),
        [Delimiter = ",", Columns = null, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    #"Changed Types" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"ReportContext", type text},
        {"ReportAsOfDate", type date},
        {"PeriodType", type text},
        {"PeriodStartDate", type date},
        {"PeriodEndDate", type date},
        {"EntityType", type text},
        {"AttributionPopulation", type text},
        {"ActiveEntityCount", Int64.Type},
        {"QualifiedEventCount", Int64.Type},
        {"EligibleEntityPopulationCap", Int64.Type}
    })
in
    #"Changed Types"
