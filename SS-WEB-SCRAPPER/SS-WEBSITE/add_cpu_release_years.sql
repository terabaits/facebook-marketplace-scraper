-- Add release year and launch price columns to cpu_reference
ALTER TABLE cpu_reference
ADD COLUMN IF NOT EXISTS release_year INTEGER,
ADD COLUMN IF NOT EXISTS launch_price_eur INTEGER;

-- Update with known release years based on processor_number patterns
-- Intel 14th Gen (Raptor Lake Refresh) - 2023
UPDATE cpu_reference SET release_year = 2023 
WHERE processor_number LIKE '14%' AND producer = 'Intel';

-- Intel 13th Gen (Raptor Lake) - 2022
UPDATE cpu_reference SET release_year = 2022 
WHERE processor_number LIKE '13%' AND producer = 'Intel';

-- Intel 12th Gen (Alder Lake) - 2021
UPDATE cpu_reference SET release_year = 2021 
WHERE processor_number LIKE '12%' AND producer = 'Intel';

-- Intel 11th Gen (Rocket Lake) - 2021
UPDATE cpu_reference SET release_year = 2021 
WHERE processor_number LIKE '11%' AND producer = 'Intel';

-- Intel 10th Gen (Comet Lake) - 2020
UPDATE cpu_reference SET release_year = 2020 
WHERE processor_number LIKE '10%' AND producer = 'Intel';

-- Intel 9th Gen (Coffee Lake Refresh) - 2018
UPDATE cpu_reference SET release_year = 2018 
WHERE processor_number LIKE '9%' AND producer = 'Intel';

-- Intel 8th Gen (Coffee Lake) - 2017
UPDATE cpu_reference SET release_year = 2017 
WHERE processor_number LIKE '8%' AND producer = 'Intel';

-- Intel 7th Gen (Kaby Lake) - 2017
UPDATE cpu_reference SET release_year = 2017 
WHERE processor_number LIKE '7%' AND producer = 'Intel';

-- Intel 6th Gen (Skylake) - 2015
UPDATE cpu_reference SET release_year = 2015 
WHERE processor_number LIKE '6%' AND producer = 'Intel';

-- AMD Ryzen 7000 series (Zen 4) - 2022
UPDATE cpu_reference SET release_year = 2022 
WHERE processor_number LIKE '7%' AND producer = 'AMD';

-- AMD Ryzen 5000 series (Zen 3) - 2020
UPDATE cpu_reference SET release_year = 2020 
WHERE processor_number LIKE '5%' AND producer = 'AMD';

-- AMD Ryzen 3000 series (Zen 2) - 2019
UPDATE cpu_reference SET release_year = 2019 
WHERE processor_number LIKE '3%' AND producer = 'AMD';

-- AMD Ryzen 2000 series (Zen+) - 2018
UPDATE cpu_reference SET release_year = 2018 
WHERE processor_number LIKE '2%' AND producer = 'AMD';

-- AMD Ryzen 1000 series (Zen) - 2017
UPDATE cpu_reference SET release_year = 2017 
WHERE processor_number LIKE '1%' AND producer = 'AMD';

-- Select to see how many have release years
SELECT producer, release_year, COUNT(*) 
FROM cpu_reference 
WHERE release_year IS NOT NULL 
GROUP BY producer, release_year 
ORDER BY producer, release_year;
